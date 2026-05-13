from dataclasses import dataclass, field
import os
import re
import tempfile

from pyproj import Transformer
from shapely import bounds, ops
from shapely.geometry import Polygon, mapping, shape

from geosprite.eo.io.raster import (
    aligned_geometry_boundary,
    crop_raster,
    gdal_to_affine,
    raster_info,
)
from geosprite.eo.store import StoreClient, auto_minio_download

_SAFE_PATH_RE = re.compile(r"[^A-Za-z0-9_.-]+")
def _empty_geometry():
    return Polygon()


def _safe_path_token(value: str) -> str:
    value = _SAFE_PATH_RE.sub("-", value.strip()).strip(".-")
    if not value:
        raise ValueError("Storage path token must contain at least one safe path character")
    return value


def _output_folder(
    spatial_key: str,
    time_key: str,
) -> str:
    spatial_key = _safe_path_token(spatial_key)
    time_key = _safe_path_token(time_key)
    path = os.path.join(tempfile.gettempdir(), "earth-raster", "crop", "results", spatial_key, time_key)
    os.makedirs(path, exist_ok=True)
    return path


def output_folder(spatial_key: str, time_key: str) -> str:
    return _output_folder(spatial_key, time_key)


def _crop_object_prefix(spatial_key: str, time_key: str) -> str:
    return f"earth-raster/crop/{_safe_path_token(spatial_key)}/{_safe_path_token(time_key)}"


def crop_output_url(spatial_key: str, time_key: str) -> str:
    object_key = _crop_object_prefix(spatial_key, time_key)
    return StoreClient().public_url(object_key)


def publish_crop_files(
    files_by_item: dict[str, dict[str, str]],
    *,
    spatial_key: str,
    time_key: str,
) -> dict[str, dict[str, str]]:
    prefix = _crop_object_prefix(spatial_key, time_key)
    urls_by_item: dict[str, dict[str, str]] = {}
    store = StoreClient()

    for item_name, files in files_by_item.items():
        safe_item_name = _safe_path_token(item_name.replace("/", "_"))
        urls_by_item[item_name] = {}
        for band_key, local_path in files.items():
            safe_band_key = _safe_path_token(band_key)
            object_key = f"{prefix}/{safe_item_name}/{safe_band_key}.tif"
            urls_by_item[item_name][band_key] = store.publish_file(
                local_path,
                object_key,
                content_type="image/tiff",
            )["url"]

    return urls_by_item


def _asset_href(asset: str | dict) -> str | None:
    if isinstance(asset, str):
        return asset
    if isinstance(asset, dict):
        href = asset.get("href")
        return href if isinstance(href, str) else None
    return None


def _download_assets(
    assets: dict[str, str | dict],
) -> dict[str, str]:
    band_keys = list(assets)
    resolved_assets = resolve_crop_assets(assets=list(assets.values()))
    return dict(zip(band_keys, resolved_assets))


@auto_minio_download(urls_param="assets")
def resolve_crop_assets(*, assets: list[str | dict]) -> list[str | dict]:
    return assets


def prepare_item_for_crop(
    item: "RasterItem",
) -> "RasterItem":
    return RasterItem(
        name=item.name,
        assets=_download_assets(item.assets),
        item_id=item.item_id,
        collection=item.collection,
        datetime=item.datetime,
        tile=item.tile,
        geometry=item.geometry,
    )


def prepare_items_for_crop(
    items_by_name: dict[str, "RasterItem"],
) -> dict[str, "RasterItem"]:
    prepared: dict[str, RasterItem] = {}
    for name, item in items_by_name.items():
        prepared[name] = prepare_item_for_crop(item)
    return prepared


def _geometry_wgs84_from_raster(raster_path: str) -> tuple[int | None, object]:
    info = raster_info(raster_path)
    if not info.crs or not info.crs.startswith("EPSG:") or not info.bounds_wgs84:
        return None, _empty_geometry()

    try:
        epsg = int(info.crs.split(":", 1)[1])
    except ValueError:
        return None, _empty_geometry()

    min_x, min_y, max_x, max_y = info.bounds_wgs84
    corners = [
        (min_x, min_y),
        (min_x, max_y),
        (max_x, max_y),
        (max_x, min_y),
        (min_x, min_y),
    ]
    return epsg, Polygon(corners)


@dataclass(frozen=True)
class RasterItem:
    name: str
    assets: dict[str, str | dict] = field(default_factory=dict)
    item_id: str | None = None
    collection: str | None = None
    datetime: str | None = None
    tile: str | None = None
    geometry: dict | None = None

    @property
    def band_keys(self) -> tuple[str, ...]:
        return tuple(self.assets.keys())

    def asset_path(self, band_key: str) -> str | None:
        asset = self.assets.get(band_key)
        return _asset_href(asset)

    def first_raster_path(self) -> str | None:
        for band_key in self.band_keys:
            path = self.asset_path(band_key)
            if path:
                return path
        return None

    def affine(self, band_key: str):
        path = self.asset_path(band_key)
        if not path:
            return None

        return gdal_to_affine(raster_info(path).geo_transform)

    def first_affine(self):
        for band_key in self.band_keys:
            affine = self.affine(band_key)
            if affine is not None:
                return affine
        return None

    def proj_epsg(self) -> int | None:
        raster_path = self.first_raster_path()
        if raster_path is None:
            return None
        epsg, _ = _geometry_wgs84_from_raster(raster_path)
        return epsg

    def valid_geometry_wgs84(self):
        if self.geometry:
            return shape(self.geometry)

        raster_path = self.first_raster_path()
        if raster_path is None:
            return _empty_geometry()
        _, geometry = _geometry_wgs84_from_raster(raster_path)
        return geometry


@dataclass(frozen=True)
class CommonExtent:
    anchor_item: str
    crs: str
    bounds: tuple[float, float, float, float]
    intersection_wgs84: dict


@dataclass(frozen=True)
class CropGroupResult:
    spatial_key: str
    time_key: str
    output_folder: str
    files_by_item: dict[str, dict[str, str]]
    extent: CommonExtent


def compute_common_extent(
    items_by_name: dict[str, RasterItem],
    anchor_item: str | None = None,
) -> CommonExtent:
    if not items_by_name:
        raise ValueError("At least one raster item is required")

    names = list(items_by_name.keys())
    anchor_name = anchor_item or names[0]
    anchor = items_by_name.get(anchor_name)
    if anchor is None:
        raise ValueError(f"Anchor item not found: {anchor_name}")

    intersection_wgs84 = None
    for item in items_by_name.values():
        geometry = item.valid_geometry_wgs84()
        if geometry.is_empty:
            raise ValueError(f"Raster item '{item.name}' has no valid geometry")
        intersection_wgs84 = geometry if intersection_wgs84 is None else intersection_wgs84.intersection(geometry)
        if intersection_wgs84.is_empty:
            raise ValueError("Raster items do not overlap")

    anchor_epsg = anchor.proj_epsg()
    if anchor_epsg is None:
        raise ValueError(f"Anchor item has no projected CRS: {anchor_name}")

    anchor_affine = anchor.first_affine()
    if anchor_affine is None:
        raise ValueError(f"Anchor item has no raster transform: {anchor_name}")

    reproj_transform = Transformer.from_crs(4326, anchor_epsg, always_xy=True).transform
    intersection_in_anchor = ops.transform(reproj_transform, intersection_wgs84)
    aligned_geometry = aligned_geometry_boundary(anchor_affine, intersection_in_anchor)
    min_x, min_y, max_x, max_y = bounds(aligned_geometry)

    return CommonExtent(
        anchor_item=anchor_name,
        crs=f"EPSG:{anchor_epsg}",
        bounds=(min_x, min_y, max_x, max_y),
        intersection_wgs84=mapping(intersection_wgs84),
    )


def crop_item_to_extent(
    item: RasterItem,
    output_folder: str,
    extent: CommonExtent,
    resampling: str = "bicubic",
) -> dict[str, str]:
    os.makedirs(output_folder, exist_ok=True)
    cropped_files: dict[str, str] = {}
    for band_key in item.band_keys:
        input_path = item.asset_path(band_key)
        if not input_path:
            continue

        info = raster_info(input_path)
        res_x, res_y = info.resolution
        output_path = os.path.join(output_folder, f"{band_key}.tif")
        cropped_files[band_key] = crop_raster(
            input_path=input_path,
            output_path=output_path,
            bounds=extent.bounds,
            crs=extent.crs,
            resampling=resampling,
            x_resolution=res_x,
            y_resolution=res_y,
        )

    return cropped_files


def crop_group_to_extent(
    items_by_name: dict[str, RasterItem],
    output_folder: str,
    extent: CommonExtent,
    resampling: str = "bicubic",
) -> dict[str, dict[str, str]]:
    files_by_item: dict[str, dict[str, str]] = {}
    for item_name, item in items_by_name.items():
        item_folder = os.path.join(output_folder, item_name.replace("/", "_"))
        files_by_item[item_name] = crop_item_to_extent(
            item=item,
            output_folder=item_folder,
            extent=extent,
            resampling=resampling,
        )
    return files_by_item


def crop_group_to_intersection(
    items_by_name: dict[str, RasterItem],
    output_folder: str,
    spatial_key: str,
    time_key: str,
    anchor_item: str | None = None,
    resampling: str = "bicubic",
) -> CropGroupResult:
    extent = compute_common_extent(items_by_name, anchor_item=anchor_item)
    files_by_item = crop_group_to_extent(
        items_by_name=items_by_name,
        output_folder=output_folder,
        extent=extent,
        resampling=resampling,
    )
    return CropGroupResult(
        spatial_key=spatial_key,
        time_key=time_key,
        output_folder=output_folder,
        files_by_item=files_by_item,
        extent=extent,
    )
