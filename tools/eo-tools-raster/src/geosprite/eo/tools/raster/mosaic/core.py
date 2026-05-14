# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

import os

from osgeo import gdal

from .geometry import read, to_json

__all__ = ["mosaic", "mosaic_json"]


def translate_cog(input_file: str, output_file: str):
    options = gdal.TranslateOptions(
        format="COG",
        creationOptions=[
            "BIGTIFF=IF_NEEDED",
            "NUM_THREADS=ALL_CPUS",
            "OVERVIEWS=IGNORE_EXISTING",
            "COMPRESS=DEFLATE",
            "PREDICTOR=2",
            "INTERLEAVE=BAND",
        ],
    )
    result = gdal.Translate(output_file, input_file, options=options)
    if result is None:
        raise RuntimeError(f"Failed to translate COG: {input_file}")
    result.Close()


def mosaic(input_files: list[str], output_file: str, cutline_geojson: str | None = None):
    import os
    import tempfile

    vrt_file = os.path.splitext(output_file)[0] + '.vrt'
    os.makedirs(os.path.dirname(vrt_file), exist_ok=True)
    vrt_options = gdal.BuildVRTOptions(resampleAlg='near', addAlpha=False)
    vrt = gdal.BuildVRT(vrt_file, input_files, options=vrt_options)
    vrt = None  # 关闭并写入 VRT 文件

    warp_kwargs = {
        'format': 'GTiff',
        'multithread': True,
        'creationOptions': ['COMPRESS=DEFLATE', 'BIGTIFF=IF_NEEDED', 'TILED=YES']
    }

    if isinstance(cutline_geojson, str):
        import shutil

        geoms = read(cutline_geojson)

        temp_dir = tempfile.mkdtemp()
        temp_geojson = os.path.join(temp_dir, 'cutline.geojson')
        to_json(temp_geojson, geoms)

        try:
            warp_kwargs.update({
                'cutlineDSName': temp_geojson,
                'cropToCutline': True,
                'dstAlpha': True  # 添加 Alpha 通道以支持透明背景
            })
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    try:
        temp_file = output_file + ".temp"
        warp_options = gdal.WarpOptions(**warp_kwargs)
        gdal.Warp(temp_file, vrt_file, options=warp_options)

        translate_cog(temp_file, output_file)
        os.remove(temp_file)

    finally:
        if os.path.exists(vrt_file):
            os.remove(vrt_file)

        if cutline_geojson and 'temp_dir' in locals():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def mosaic_json(file: str, assets: list[str]):

    def quadkeys_from_bounds(bounds: list[float], quadkey_zoom: int) -> list[str]:
        """
        从已知边界生成 Quadkey 列表

        Args:
            bounds: 包含 'west', 'south', 'east', 'north' 的字典
            quadkey_zoom: 目标 Quadkey 缩放级别

        Returns:
            Quadkey 字符串列表
        """

        import mercantile

        tiles = mercantile.tiles(*tuple(bounds), zooms=quadkey_zoom)

        return [mercantile.quadkey(tile) for tile in tiles]

    import json
    from collections import defaultdict
    from geosprite.eo.io.raster import RasterDataset

    tiles_dict = defaultdict(list)

    union_bounds = {
        'west': 180.0,
        'east': -180.0,
        'south': 90.0,
        'north': -90.0
    }

    for asset in assets:

        try:
            dataset = RasterDataset(asset)
        except Exception as e:
            raise RuntimeError("Can not open dataset {}".format(asset))

        bounds = dataset.bounds
        geo_transform = dataset.profile.geo_transform
        minzoom, maxzoom = dataset.zoom_levels(min(abs(geo_transform[1]), abs(geo_transform[5])))

        quadkeys = quadkeys_from_bounds(bounds, minzoom)

        # 将资产添加到对应的 Quadkey 中
        for quadkey in quadkeys:
            tiles_dict[quadkey].append(asset)

        # 更新联合边界
        union_bounds['west'] = min(union_bounds['west'], bounds[0])
        union_bounds['east'] = max(union_bounds['east'], bounds[2])
        union_bounds['south'] = min(union_bounds['south'], bounds[1])
        union_bounds['north'] = max(union_bounds['north'], bounds[3])

        content = {
            "mosaicjson": "0.0.3",
            "version": "1.0.0",
            "minzoom": minzoom,
            "maxzoom": maxzoom,
            "quadkey_zoom": minzoom,
            "bounds": [union_bounds['west'], union_bounds['south'], union_bounds['east'], union_bounds['north']],
            "center": [(union_bounds['west'] + union_bounds['east']) / 2,
                       (union_bounds['south'] + union_bounds['north']) / 2, minzoom],
            "tiles": tiles_dict
        }

        os.makedirs(os.path.dirname(file), exist_ok=True)

        with open(file, 'w') as f:
            json.dump(content, f, indent=2)
