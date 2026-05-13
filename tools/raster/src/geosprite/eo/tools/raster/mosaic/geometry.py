# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from osgeo import ogr
from shapely.geometry import shape, Polygon, GeometryCollection
from shapely.geometry.base import BaseGeometry


def read(geojson: str | dict) -> GeometryCollection | None:

    if isinstance(geojson, dict) or isinstance(geojson, str):
        import ast

        if isinstance(geojson, str):
            geojson = ast.literal_eval(geojson)

        if "features" in geojson:
            features: dict = geojson["features"]
            return GeometryCollection([shape(feature["geometry"]) for feature in features])
        elif "geometry" in geojson:
            return GeometryCollection([shape(geojson["geometry"])])
        elif "coordinates" in geojson and "type" in geojson:
            return GeometryCollection([shape(geojson)])
        else:
            return None


def intersect(geojson: str, bbox: tuple[float, float, float, float]) -> BaseGeometry:
    geometries = read(geojson)

    x1, y1, x2, y2 = bbox
    poly = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
    return geometries.intersection(poly)


def to_json(geojson_file: str, geometry: BaseGeometry, geom_type: int = ogr.wkbPolygon, layer_name: str | None = "layer") -> None:
    driver = ogr.GetDriverByName('GeoJSON')
    ds = driver.CreateDataSource(geojson_file)
    layer = ds.CreateLayer(layer_name, geom_type=geom_type)

    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(geometry)
    layer.CreateFeature(feature)
