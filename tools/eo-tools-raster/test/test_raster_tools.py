from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from osgeo import gdal, osr
from pydantic import ValidationError

from geosprite.eo.tools import build_registry_from_package
from geosprite.eo.tools.raster.composition import ComposeRasterIn, ComposeRasterTool
from geosprite.eo.tools.raster.stack import (
    StackRasterIn,
    StackRasterTool,
    StackRgbRasterIn,
    StackRgbRasterTool,
)


def _wgs84() -> str:
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    return srs.ExportToWkt()


def _write_tiff(path: Path, value: int) -> None:
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), 1, 1, 1, gdal.GDT_Int16)
    dataset.SetProjection(_wgs84())
    dataset.SetGeoTransform((0, 1, 0, 1, 0, -1))
    dataset.GetRasterBand(1).WriteArray(np.array([[value]], dtype=np.int16))
    dataset.FlushCache()
    close = getattr(dataset, "Close", None)
    if callable(close):
        close()


@dataclass
class _Context:
    store: object | None
    workdir: Path
    logger: logging.Logger = logging.getLogger("eo-tools-raster-test")
    run_id: str | None = "test-run"


@dataclass
class _FetchResult:
    local_path: Path


class _Store:
    def __init__(self, sources: dict[str, Path]):
        self.sources = sources
        self.fetches: list[tuple[str, Path]] = []

    def fetch(self, source_uri: str, destination_path: str | Path, **kwargs):
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.sources[source_uri], destination)
        self.fetches.append((source_uri, destination))
        return _FetchResult(destination)


class RasterToolTests(unittest.TestCase):
    def test_stack_tool_runs_local_operator_to_local_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            output = root / "stack.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=None, workdir=root),
                    StackRasterIn(
                        input_files=[str(left), str(right)],
                        output_file=str(output),
                    ),
                )
            )

            stacked = gdal.Open(result.local_path)
            self.assertEqual(stacked.RasterCount, 2)
            self.assertEqual(stacked.GetMetadata("IMAGE_STRUCTURE").get("LAYOUT"), "COG")
            self.assertEqual(result.destination_uri, None)
            self.assertEqual(result.write_back, True)
            self.assertEqual(result.presigned_url, None)
            close = getattr(stacked, "Close", None)
            if callable(close):
                close()

    def test_stack_tool_can_override_output_format_to_geotiff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            output = root / "stack.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=None, workdir=root),
                    StackRasterIn(
                        input_files=[str(left), str(right)],
                        output_file=str(output),
                        output_format="GTiff",
                    ),
                )
            )

            stacked = gdal.Open(result.local_path)
            try:
                self.assertEqual(stacked.RasterCount, 2)
                image_structure = stacked.GetMetadata("IMAGE_STRUCTURE")
                self.assertEqual(image_structure.get("COMPRESSION"), "DEFLATE")
                self.assertEqual(image_structure.get("INTERLEAVE"), "BAND")
                self.assertEqual(image_structure.get("PREDICTOR"), "2")
            finally:
                close = getattr(stacked, "Close", None)
                if callable(close):
                    close()

    def test_stack_tool_writes_relative_output_under_workdir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=None, workdir=root / "work"),
                    StackRasterIn(
                        input_files=[str(left), str(right)],
                        output_file="products/stack.tif",
                    ),
                )
            )

            expected_output = root / "work" / "products" / "stack.tif"
            self.assertEqual(Path(result.local_path), expected_output)
            self.assertTrue(expected_output.is_file())
            self.assertEqual(result.destination_uri, None)
            self.assertEqual(result.write_back, True)

    def test_stack_tool_localizes_uri_inputs_before_local_operator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            output = root / "work" / "stack.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)
            left_uri = "https://example.test/assets/left.tif"
            right_uri = "https://example.test/assets/right.tif"
            store = _Store({left_uri: left, right_uri: right})

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    StackRasterIn(
                        input_files=[left_uri, right_uri],
                        output_file=str(output),
                    ),
                )
            )

            stacked = gdal.Open(result.local_path)
            self.assertEqual(stacked.RasterCount, 2)
            self.assertEqual([item[0] for item in store.fetches], [left_uri, right_uri])
            self.assertTrue(
                all((root / "work") in path.parents for _, path in store.fetches)
            )
            self.assertEqual(
                [path.parts[-2:] for _, path in store.fetches],
                [("assets", "left.tif"), ("assets", "right.tif")],
            )
            close = getattr(stacked, "Close", None)
            if callable(close):
                close()

    def test_stack_tool_requires_store_for_uri_inputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with self.assertRaisesRegex(ValueError, "Store"):
                asyncio.run(
                    StackRasterTool().run(
                        _Context(store=None, workdir=root),
                        StackRasterIn(
                            input_files=["https://example.test/assets/left.tif"],
                            output_file=str(root / "stack.tif"),
                        ),
                    )
                )

    def test_stack_tool_reuses_existing_local_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            output = root / "work" / "products" / "stack.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)
            output.parent.mkdir(parents=True, exist_ok=True)
            _write_tiff(output, 7)

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=None, workdir=root / "work"),
                    StackRasterIn(
                        input_files=[str(left), str(right)],
                        output_file="products/stack.tif",
                    ),
                )
            )

            self.assertEqual(Path(result.local_path), output)
            self.assertEqual(result.destination_uri, None)
            self.assertEqual(result.write_back, False)

    def test_stack_tool_rejects_s3_output(self):
        with self.assertRaises(ValidationError):
            StackRasterIn(
                input_files=["source.tif"],
                output_file="s3://products/stack.tif",
            )

    def test_stack_rgb_tool_runs_local_operator_to_local_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            red = root / "red.tif"
            green = root / "green.tif"
            blue = root / "blue.tif"
            output = root / "rgb.tif"
            _write_tiff(red, 10)
            _write_tiff(green, 20)
            _write_tiff(blue, 30)

            result = asyncio.run(
                StackRgbRasterTool().run(
                    _Context(store=None, workdir=root),
                    StackRgbRasterIn(
                        input_files=[str(red), str(green), str(blue)],
                        output_file=str(output),
                    ),
                )
            )

            stacked = gdal.Open(result.local_path)
            try:
                image_structure = stacked.GetMetadata("IMAGE_STRUCTURE")
                self.assertEqual(stacked.RasterCount, 3)
                self.assertEqual(stacked.GetRasterBand(1).DataType, gdal.GDT_Byte)
                self.assertEqual(stacked.GetRasterBand(1).GetColorInterpretation(), gdal.GCI_RedBand)
                self.assertEqual(stacked.GetRasterBand(2).GetColorInterpretation(), gdal.GCI_GreenBand)
                self.assertEqual(stacked.GetRasterBand(3).GetColorInterpretation(), gdal.GCI_BlueBand)
                self.assertEqual(image_structure.get("LAYOUT"), "COG")
                self.assertIn("JPEG", image_structure.get("COMPRESSION", ""))
                self.assertEqual(result.destination_uri, None)
                self.assertEqual(result.write_back, True)
            finally:
                close = getattr(stacked, "Close", None)
                if callable(close):
                    close()

    def test_stack_rgb_tool_can_write_jpeg_compressed_cog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            red = root / "red.tif"
            green = root / "green.tif"
            blue = root / "blue.tif"
            output = root / "rgb-jpeg-cog.tif"
            _write_tiff(red, 10)
            _write_tiff(green, 20)
            _write_tiff(blue, 30)

            result = asyncio.run(
                StackRgbRasterTool().run(
                    _Context(store=None, workdir=root),
                    StackRgbRasterIn(
                        input_files=[str(red), str(green), str(blue)],
                        output_file=str(output),
                        output_format="JPEG_COG",
                    ),
                )
            )

            stacked = gdal.Open(result.local_path)
            try:
                image_structure = stacked.GetMetadata("IMAGE_STRUCTURE")
                self.assertEqual(stacked.RasterCount, 3)
                self.assertEqual(stacked.GetRasterBand(1).DataType, gdal.GDT_Byte)
                self.assertEqual(image_structure.get("LAYOUT"), "COG")
                self.assertIn("JPEG", image_structure.get("COMPRESSION", ""))
            finally:
                close = getattr(stacked, "Close", None)
                if callable(close):
                    close()

    def test_stack_rgb_tool_requires_three_inputs(self):
        with self.assertRaises(ValidationError):
            StackRgbRasterIn(
                input_files=["red.tif", "green.tif"],
                output_file="rgb.tif",
            )

    def test_compose_tool_runs_local_operator_to_local_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 9)
            output = root / "max.tif"

            result = asyncio.run(
                ComposeRasterTool().run(
                    _Context(store=None, workdir=root),
                    ComposeRasterIn(
                        input_files=[str(left), str(right)],
                        output_file=str(output),
                        method="max",
                    ),
                )
            )

            composed = gdal.Open(result.local_path)
            self.assertEqual(composed.GetRasterBand(1).ReadAsArray().item(), 9)
            self.assertEqual(result.destination_uri, None)
            self.assertEqual(result.write_back, True)
            close = getattr(composed, "Close", None)
            if callable(close):
                close()

    def test_publish_catalog_true_is_explicitly_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.tif"
            _write_tiff(source, 1)

            with self.assertRaises(NotImplementedError):
                asyncio.run(
                    StackRasterTool().run(
                        _Context(store=None, workdir=root),
                        StackRasterIn(
                            input_files=[str(source)],
                            output_file=str(root / "stack.tif"),
                            publish_catalog=True,
                        ),
                    )
                )

    def test_legacy_output_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            ComposeRasterIn(
                input_files=["s3://assets/left.tif"],
                output_uri="s3://products/max.tif",
            )
        with self.assertRaises(ValidationError):
            ComposeRasterIn(
                input_files=["s3://assets/left.tif"],
                output_file="max.tif",
                write_back=True,
            )

    def test_package_discovery_registers_stack_and_compose(self):
        registry = build_registry_from_package("geosprite.eo.tools.raster")

        self.assertEqual(
            {tool.fully_qualified_name() for tool in registry},
            {"raster.compose", "raster.stack", "raster.stack_rgb"},
        )


if __name__ == "__main__":
    unittest.main()
