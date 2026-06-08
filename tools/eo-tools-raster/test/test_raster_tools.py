from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from osgeo import gdal, osr
from pydantic import ValidationError

from geosprite.eo.store import Checksum, LocalizationIn, Output
from geosprite.eo.tools import build_registry_from_package
from geosprite.eo.tools.raster.composition import ComposeRasterIn, ComposeRasterTool
from geosprite.eo.tools.raster.fetch import FetchRasterIn, FetchRasterTool
from geosprite.eo.tools.raster.localization import LocalizeRasterTool
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
    source_uri: str
    resolved_uri: str
    backend: str
    size: int
    checksum: Checksum


@dataclass
class _PutResult:
    destination_uri: str


@dataclass
class _PresignResult:
    url: str


class _Store:
    def __init__(
        self,
        sources: dict[str, Path] | None = None,
        existing: set[str] | None = None,
    ):
        self.sources = sources or {}
        self.existing = existing or set()
        self.fetches: list[tuple[str, Path]] = []
        self.puts: list[tuple[Path, str, bool]] = []
        self.presigns: list[tuple[str, int]] = []

    def fetch(self, source_uri: str, destination_path: str | Path, **kwargs):
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.sources[source_uri], destination)
        self.fetches.append((source_uri, destination))
        payload = destination.read_bytes()
        return _FetchResult(
            local_path=destination,
            source_uri=source_uri,
            resolved_uri=source_uri,
            backend="test-store",
            size=len(payload),
            checksum=Checksum(value=hashlib.sha256(payload).hexdigest()),
        )

    def exists(self, source_uri: str) -> bool:
        return source_uri in self.existing

    def put(self, local_path: str | Path, destination_uri: str, **kwargs):
        source = Path(local_path)
        if not source.is_file():
            raise AssertionError(f"put source does not exist: {source}")
        self.puts.append((source, destination_uri, bool(kwargs.get("overwrite", False))))
        self.existing.add(destination_uri)
        return _PutResult(destination_uri)

    def presign(self, source_uri: str, *, expires_in: int = 3600):
        self.presigns.append((source_uri, expires_in))
        return _PresignResult(f"https://signed.example.test/{source_uri.removeprefix('s3://')}")


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

    def test_stack_tool_writes_s3_output_through_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)
            destination = "s3://products/stack.tif"
            store = _Store()

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    StackRasterIn(
                        input_files=[str(left), str(right)],
                        output_file=destination,
                        overwrite=True,
                    ),
                )
            )

            self.assertEqual(result.destination_uri, destination)
            self.assertEqual(result.presigned_url, None)
            self.assertEqual(result.write_back, True)
            self.assertEqual(len(store.puts), 1)
            put_path, put_uri, put_overwrite = store.puts[0]
            self.assertEqual(put_uri, destination)
            self.assertEqual(put_overwrite, True)
            self.assertEqual(Path(result.local_path), put_path)
            self.assertTrue(put_path.is_file())
            self.assertEqual(
                put_path,
                root / "work" / "test-run" / "products" / "stack.tif",
            )

    def test_raster_output_omits_absent_run_id_from_remote_stage_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            for run_id in (None, "", " ", "none", "None"):
                with self.subTest(run_id=run_id):
                    output = Output.from_context(
                        _Store(),
                        root / "work",
                        "s3://products/stack.tif",
                        "stack.tif",
                        run_id=run_id,
                    )

                    self.assertEqual(
                        output.local_path,
                        root / "work" / "products" / "stack.tif",
                    )

    def test_stack_tool_normalizes_directory_s3_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)
            store = _Store()

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    StackRasterIn(
                        input_files=[str(left), str(right)],
                        output_file="s3://products/outputs/",
                    ),
                )
            )

            expected_destination = "s3://products/outputs/stack.tif"
            self.assertEqual(result.destination_uri, expected_destination)
            self.assertEqual(len(store.puts), 1)
            put_path, put_uri, _ = store.puts[0]
            self.assertEqual(put_uri, expected_destination)
            self.assertEqual(Path(result.local_path), put_path)
            self.assertEqual(
                put_path,
                root
                / "work"
                / "test-run"
                / "products"
                / "outputs"
                / "stack.tif",
            )

    def test_stack_tool_reuses_existing_s3_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            destination = "s3://products/stack.tif"
            store = _Store(existing={destination})

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    StackRasterIn(
                        input_files=[str(root / "missing-left.tif"), str(root / "missing-right.tif")],
                        output_file=destination,
                    ),
                )
            )

            self.assertEqual(result.local_path, None)
            self.assertEqual(result.destination_uri, destination)
            self.assertEqual(result.write_back, False)
            self.assertEqual(store.puts, [])

    def test_stack_tool_presigns_existing_s3_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            destination = "s3://products/stack.tif"
            store = _Store(existing={destination})

            result = asyncio.run(
                StackRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    StackRasterIn(
                        input_files=[str(root / "missing-left.tif"), str(root / "missing-right.tif")],
                        output_file=destination,
                        presign_url=True,
                        presign_expires_in=900,
                    ),
                )
            )

            self.assertEqual(result.presigned_url, "https://signed.example.test/products/stack.tif")
            self.assertEqual(store.presigns, [(destination, 900)])

    def test_stack_tool_requires_store_for_s3_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.tif"
            _write_tiff(source, 1)

            with self.assertRaisesRegex(ValueError, "requires a store"):
                asyncio.run(
                    StackRasterTool().run(
                        _Context(store=None, workdir=root),
                        StackRasterIn(
                            input_files=[str(source)],
                            output_file="s3://products/stack.tif",
                        ),
                    )
                )

    def test_presign_url_requires_s3_output(self):
        with self.assertRaises(ValidationError):
            StackRasterIn(
                input_files=["source.tif"],
                output_file="stack.tif",
                presign_url=True,
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

    def test_stack_rgb_tool_writes_s3_output_through_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            red = root / "red.tif"
            green = root / "green.tif"
            blue = root / "blue.tif"
            _write_tiff(red, 10)
            _write_tiff(green, 20)
            _write_tiff(blue, 30)
            destination = "s3://geosprite/eo/raster/TCI.tif"
            store = _Store()

            result = asyncio.run(
                StackRgbRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    StackRgbRasterIn(
                        input_files=[str(red), str(green), str(blue)],
                        output_file=destination,
                        overwrite=True,
                    ),
                )
            )

            self.assertEqual(result.destination_uri, destination)
            self.assertEqual(result.write_back, True)
            self.assertEqual(len(store.puts), 1)
            put_path, put_uri, _ = store.puts[0]
            self.assertEqual(put_uri, destination)
            self.assertEqual(Path(result.local_path), put_path)
            self.assertEqual(
                put_path,
                root
                / "work"
                / "test-run"
                / "geosprite"
                / "eo"
                / "raster"
                / "TCI.tif",
            )
            stacked = gdal.Open(str(put_path))
            try:
                self.assertEqual(stacked.RasterCount, 3)
                self.assertEqual(stacked.GetRasterBand(1).DataType, gdal.GDT_Byte)
            finally:
                close = getattr(stacked, "Close", None)
                if callable(close):
                    close()

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

    def test_fetch_tool_downloads_source_to_local_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.tif"
            output = root / "work" / "downloads" / "source.tif"
            _write_tiff(source, 3)
            source_uri = "https://example.test/assets/source.tif"
            store = _Store({source_uri: source})

            result = asyncio.run(
                FetchRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    FetchRasterIn(
                        source_uri=source_uri,
                        output_file="downloads/source.tif",
                    ),
                )
            )

            self.assertEqual(Path(result.local_path), output)
            self.assertTrue(output.is_file())
            self.assertEqual(result.destination_uri, None)
            self.assertEqual(result.presigned_url, None)
            self.assertEqual(result.write_back, True)
            self.assertEqual(store.fetches, [(source_uri, output)])
            self.assertEqual(store.puts, [])

    def test_fetch_tool_uploads_to_s3_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.tif"
            _write_tiff(source, 4)
            source_uri = "https://example.test/assets/source.tif"
            destination = "s3://products/raw/source.tif"
            store = _Store({source_uri: source})

            result = asyncio.run(
                FetchRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    FetchRasterIn(
                        source_uri=source_uri,
                        output_file=destination,
                        presign_url=True,
                        presign_expires_in=600,
                    ),
                )
            )

            expected_local = root / "work" / "test-run" / "products" / "raw" / "source.tif"
            self.assertEqual(Path(result.local_path), expected_local)
            self.assertEqual(result.destination_uri, destination)
            self.assertEqual(result.presigned_url, "https://signed.example.test/products/raw/source.tif")
            self.assertEqual(result.write_back, True)
            self.assertEqual(store.fetches, [(source_uri, expected_local)])
            self.assertEqual(store.puts, [(expected_local, destination, False)])
            self.assertEqual(store.presigns, [(destination, 600)])

    def test_fetch_tool_accepts_s3_output_file_as_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.tif"
            _write_tiff(source, 5)
            source_uri = "https://example.test/assets/source.tif"
            destination = "s3://products/raw/"
            store = _Store({source_uri: source})

            result = asyncio.run(
                FetchRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    FetchRasterIn(
                        source_uri=source_uri,
                        output_file=destination,
                    ),
                )
            )

            expected_destination = "s3://products/raw/source.tif"
            self.assertEqual(result.destination_uri, expected_destination)
            self.assertEqual(store.puts[0][1], expected_destination)

    def test_fetch_tool_skips_existing_s3_destination_without_local_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_uri = "https://example.test/assets/source.tif"
            destination = "s3://products/raw/source.tif"
            store = _Store(existing={destination})

            result = asyncio.run(
                FetchRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    FetchRasterIn(
                        source_uri=source_uri,
                        output_file=destination,
                    ),
                )
            )

            self.assertEqual(result.local_path, None)
            self.assertEqual(result.destination_uri, destination)
            self.assertEqual(result.write_back, False)
            self.assertEqual(store.fetches, [])
            self.assertEqual(store.puts, [])

    def test_fetch_tool_requires_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "requires a store"):
                asyncio.run(
                    FetchRasterTool().run(
                        _Context(store=None, workdir=Path(temp_dir)),
                        FetchRasterIn(source_uri="https://example.test/assets/source.tif"),
                    )
                )

    def test_fetch_tool_rejects_legacy_destination_uri(self):
        with self.assertRaises(ValidationError):
            FetchRasterIn(
                source_uri="https://example.test/assets/source.tif",
                destination_uri="file:///tmp/source.tif",
            )

    def test_localization_tool_localizes_multiple_uri_inputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left = root / "left.tif"
            right = root / "right.tif"
            _write_tiff(left, 1)
            _write_tiff(right, 2)
            left_uri = "https://example.test/assets/left.tif"
            right_uri = "https://example.test/assets/right.tif"
            store = _Store({left_uri: left, right_uri: right})

            result = asyncio.run(
                LocalizeRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    LocalizationIn(input_files=[left_uri, right_uri]),
                )
            )

            self.assertEqual([item[0] for item in store.fetches], [left_uri, right_uri])
            self.assertEqual(result.input_files, [str(path) for _, path in store.fetches])
            self.assertTrue(
                all((root / "work") in Path(path).parents for path in result.input_files)
            )
            self.assertEqual(
                [Path(path).parts[-2:] for path in result.input_files],
                [("assets", "left.tif"), ("assets", "right.tif")],
            )
            self.assertEqual(result.publish_catalog, False)

    def test_localization_tool_reuses_existing_localized_s3_uri(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_uri = "https://example.test/assets/source.tif"
            localized_uri = "s3://geosprite/localized/https-example.test/assets/source.tif"
            store = _Store(existing={localized_uri})

            result = asyncio.run(
                LocalizeRasterTool().run(
                    _Context(store=store, workdir=root / "work"),
                    LocalizationIn(
                        input_files=[source_uri],
                        bucket="geosprite",
                        prefix="localized",
                    ),
                )
            )

            self.assertEqual(result.input_files, [localized_uri])
            self.assertEqual(store.fetches, [])
            self.assertEqual(store.puts, [])

    def test_package_discovery_registers_raster_tools(self):
        registry = build_registry_from_package("geosprite.eo.tools.raster")

        self.assertEqual(
            {tool.fully_qualified_name() for tool in registry},
            {
                "raster.compose",
                "raster.fetch",
                "raster.localization",
                "raster.stack",
                "raster.stack_rgb",
            },
        )


if __name__ == "__main__":
    unittest.main()
