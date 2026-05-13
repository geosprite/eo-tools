from dataclasses import dataclass
import math
from typing import Iterable

from shapely import bounds as geometry_bounds
from shapely.geometry import box

@dataclass(frozen=True)
class RasterWindow:
    col_off: int
    row_off: int
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.col_off, self.row_off, self.width, self.height


@dataclass(frozen=True)
class AffineCoefficients:
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float


def affine_coefficients(affine) -> AffineCoefficients:
    if all(hasattr(affine, attr) for attr in ("a", "b", "c", "d", "e", "f")):
        return AffineCoefficients(
            a=float(affine.a),
            b=float(affine.b),
            c=float(affine.c),
            d=float(affine.d),
            e=float(affine.e),
            f=float(affine.f),
        )

    values = tuple(affine)
    if len(values) == 6:
        return AffineCoefficients(
            a=float(values[0]),
            b=float(values[1]),
            c=float(values[2]),
            d=float(values[3]),
            e=float(values[4]),
            f=float(values[5]),
        )
    if len(values) >= 9:
        return AffineCoefficients(
            a=float(values[0]),
            b=float(values[1]),
            c=float(values[2]),
            d=float(values[3]),
            e=float(values[4]),
            f=float(values[5]),
        )

    raise ValueError("Affine must expose a/b/c/d/e/f attributes or be a 6/9-value iterable")


def gdal_to_affine(geo_transform: Iterable[float]) -> AffineCoefficients:
    gt = tuple(geo_transform)
    if len(gt) != 6:
        raise ValueError("GDAL geotransform must have 6 values")

    return AffineCoefficients(
        a=float(gt[1]),
        b=float(gt[2]),
        c=float(gt[0]),
        d=float(gt[4]),
        e=float(gt[5]),
        f=float(gt[3]),
    )


def is_orthogonal_affine(affine) -> bool:
    coeffs = affine_coefficients(affine)
    return coeffs.b == 0 and coeffs.d == 0


def pixel_to_world(affine, col: float, row: float) -> tuple[float, float]:
    coeffs = affine_coefficients(affine)
    x = coeffs.c + col * coeffs.a + row * coeffs.b
    y = coeffs.f + col * coeffs.d + row * coeffs.e
    return x, y


def world_to_pixel(affine, x: float, y: float) -> tuple[float, float]:
    coeffs = affine_coefficients(affine)
    determinant = coeffs.a * coeffs.e - coeffs.b * coeffs.d
    if determinant == 0:
        raise ValueError("Affine transform is not invertible")

    dx = x - coeffs.c
    dy = y - coeffs.f
    col = (coeffs.e * dx - coeffs.b * dy) / determinant
    row = (-coeffs.d * dx + coeffs.a * dy) / determinant
    return col, row


def window_to_geometry(affine, window: RasterWindow | tuple[int, int, int, int]):
    if not isinstance(window, RasterWindow):
        window = RasterWindow(*window)

    left = window.col_off
    top = window.row_off
    right = left + window.width
    bottom = top + window.height

    points = [
        pixel_to_world(affine, left, top),
        pixel_to_world(affine, right, top),
        pixel_to_world(affine, right, bottom),
        pixel_to_world(affine, left, bottom),
    ]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return box(min(xs), min(ys), max(xs), max(ys))


def geometry_to_window(affine, geometry) -> RasterWindow:
    if not is_orthogonal_affine(affine):
        raise ValueError("Only orthogonal affine transforms are supported")

    min_x, min_y, max_x, max_y = geometry_bounds(geometry)
    col1, row1 = world_to_pixel(affine, min_x, max_y)
    col2, row2 = world_to_pixel(affine, max_x, min_y)

    col_off = math.floor(min(col1, col2))
    row_off = math.floor(min(row1, row2))
    col_max = math.ceil(max(col1, col2))
    row_max = math.ceil(max(row1, row2))

    return RasterWindow(
        col_off=col_off,
        row_off=row_off,
        width=max(0, col_max - col_off),
        height=max(0, row_max - row_off),
    )


def aligned_geometry_boundary(affine, geometry):
    return window_to_geometry(affine, geometry_to_window(affine, geometry))
