import os
from dataclasses import dataclass
from urllib.parse import urlparse

from osgeo import gdal, osr


gdal.UseExceptions()


@dataclass(frozen=True)
class RasterInfo:
    path: str
    width: int
    height: int
    band_count: int
    crs: str | None
    bounds: tuple[float, float, float, float]
    bounds_wgs84: tuple[float, float, float, float] | None
    resolution: tuple[float, float]
    geo_transform: tuple[float, float, float, float, float, float]
    nodata: float | int | None
    data_type: str

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "band_count": self.band_count,
            "crs": self.crs,
            "bounds": self.bounds,
            "bounds_wgs84": self.bounds_wgs84,
            "resolution": self.resolution,
            "geo_transform": self.geo_transform,
            "nodata": self.nodata,
            "data_type": self.data_type,
        }


RESAMPLING_ALIASES = {
    "nearest": gdal.GRA_NearestNeighbour,
    "near": gdal.GRA_NearestNeighbour,
    "bilinear": gdal.GRA_Bilinear,
    "cubic": gdal.GRA_Cubic,
    "bicubic": gdal.GRA_Cubic,
    "cubicspline": gdal.GRA_CubicSpline,
    "lanczos": gdal.GRA_Lanczos,
    "average": gdal.GRA_Average,
    "mode": gdal.GRA_Mode,
    "max": gdal.GRA_Max,
    "min": gdal.GRA_Min,
    "med": gdal.GRA_Med,
    "median": gdal.GRA_Med,
    "q1": gdal.GRA_Q1,
    "q3": gdal.GRA_Q3,
}


def dataset_path(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return f"/vsicurl/{path}"
    if path.startswith("s3://"):
        parsed = urlparse(path)
        return f"/vsis3/{parsed.netloc}/{parsed.path.lstrip('/')}"
    return path


def normalize_resampling(name: str) -> int:
    key = name.strip().lower()
    if key not in RESAMPLING_ALIASES:
        supported = ", ".join(sorted(RESAMPLING_ALIASES))
        raise ValueError(f"Unsupported resampling '{name}'. Supported: {supported}")
    return RESAMPLING_ALIASES[key]


def _dataset_crs(dataset: gdal.Dataset) -> tuple[str | None, osr.SpatialReference | None]:
    projection = dataset.GetProjection()
    if not projection:
        return None, None

    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromWkt(projection)
    spatial_ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    authority = spatial_ref.GetAuthorityCode(None)
    if authority:
        return f"EPSG:{authority}", spatial_ref
    return spatial_ref.ExportToWkt(), spatial_ref


def _bounds_from_dataset(dataset: gdal.Dataset) -> tuple[float, float, float, float]:
    gt = dataset.GetGeoTransform()
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    corners = [
        (0, 0),
        (width, 0),
        (width, height),
        (0, height),
    ]
    points = []
    for col, row in corners:
        x = gt[0] + col * gt[1] + row * gt[2]
        y = gt[3] + col * gt[4] + row * gt[5]
        points.append((x, y))

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _transform_bounds(
    bounds: tuple[float, float, float, float],
    source_ref: osr.SpatialReference | None,
    target_epsg: int,
) -> tuple[float, float, float, float] | None:
    if source_ref is None:
        return None

    target_ref = osr.SpatialReference()
    target_ref.ImportFromEPSG(target_epsg)
    target_ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source_ref, target_ref)
    min_x, min_y, max_x, max_y = bounds
    points = [
        transform.TransformPoint(min_x, min_y),
        transform.TransformPoint(min_x, max_y),
        transform.TransformPoint(max_x, max_y),
        transform.TransformPoint(max_x, min_y),
    ]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def raster_info(path: str) -> RasterInfo:
    readable_path = dataset_path(path)
    dataset = gdal.Open(readable_path, gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"Failed to open raster: {path}")

    try:
        crs, spatial_ref = _dataset_crs(dataset)
        bounds = _bounds_from_dataset(dataset)
        first_band = dataset.GetRasterBand(1)
        nodata = first_band.GetNoDataValue() if first_band is not None else None
        data_type = gdal.GetDataTypeName(first_band.DataType) if first_band is not None else "Unknown"
        gt = dataset.GetGeoTransform()
        return RasterInfo(
            path=path,
            width=dataset.RasterXSize,
            height=dataset.RasterYSize,
            band_count=dataset.RasterCount,
            crs=crs,
            bounds=bounds,
            bounds_wgs84=_transform_bounds(bounds, spatial_ref, 4326),
            resolution=(abs(gt[1]), abs(gt[5])),
            geo_transform=tuple(gt),
            nodata=nodata,
            data_type=data_type,
        )
    finally:
        dataset.Close()


def crop_raster(
    input_path: str,
    output_path: str,
    bounds: tuple[float, float, float, float],
    *,
    crs: str,
    resampling: str = "bicubic",
    x_resolution: float | None = None,
    y_resolution: float | None = None,
    creation_options: list[str] | None = None,
) -> str:
    output_dir = os.path.dirname(output_path)
    if output_dir and not output_path.startswith("/vsi"):
        os.makedirs(output_dir, exist_ok=True)

    options = gdal.WarpOptions(
        format="GTiff",
        outputBounds=bounds,
        outputBoundsSRS=crs,
        dstSRS=crs,
        xRes=x_resolution,
        yRes=y_resolution,
        resampleAlg=normalize_resampling(resampling),
        creationOptions=creation_options
        or ["COMPRESS=DEFLATE", "TILED=YES", "BIGTIFF=IF_NEEDED"],
    )
    result = gdal.Warp(output_path, dataset_path(input_path), options=options)
    if result is None:
        raise RuntimeError(f"Failed to crop raster: {input_path}")
    result.Close()
    return output_path
