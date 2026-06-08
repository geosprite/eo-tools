# Copyright (c) GeoSprite. All rights reserved.
#
# Author: JH Zhang
#

"""
Sentinel-1 Preprocessing Module
Requires ESA SNAP with snappy Python bindings
"""

import os

try:
    from esa_snappy import GPF, HashMap, ProductIO, jpy
except ImportError as exc:
    _SNAP_IMPORT_ERROR = exc
    ProductIO = None
    GPF = None
    HashMap = None
    jpy = None
else:
    _SNAP_IMPORT_ERROR = None


def output_files(
    input_file: str,
    polar_list: list[str],
    output_dir: str,
    prefix: str = "iw-",
) -> list[str]:
    resolved_dir = os.path.join(output_dir, os.path.dirname(input_file))
    os.makedirs(resolved_dir, exist_ok=True)

    return [
        os.path.join(resolved_dir, prefix + pol + ".tif")
        for pol in polar_list
    ]

def preprocess(
    input_file: str,
    polar_list: list[str],
    output_dir: str,
) -> list[str]:
    """
    Preprocess Sentinel-1 GRD data.

    Args:
        input_file: Path to Sentinel-1 .SAFE file or manifest.safe
        polar_list: List of polarizations to process (e.g., ['VV', 'VH'])
        output_dir: Output directory (default: same as input file)

    Returns:
        List of output file paths

    Raises:
        ImportError: If esa_snappy is not available
        RuntimeError: If processing fails
    """
    # if _SNAP_IMPORT_ERROR is not None:
    #     raise ImportError(
    #         "ESA SNAP snappy module is not installed. "
    #         "Please install SNAP and configure snappy Python bindings."
    #     ) from _SNAP_IMPORT_ERROR

    outputs = output_files(input_file, polar_list, output_dir)

    for pol, output_file in zip(polar_list, outputs):
        print("Processing Sentinel-1 data:")
        print(f"  Input: {input_file}")
        print(f"  Polarization: {pol}")
        print(f"  Output: {output_file}")

        if os.path.isfile(output_file):
            print("  File already exists, skipping.")
            continue

        print("  Starting processing pipeline...")

        # p = ProductIO.readProduct(input_file)
        # p = _apply_orbit_file(p, jpy)
        # p = _thermal_noise_removal(p)
        # p = _remove_border_noise(p, jpy)
        # p = _calibration(p, [pol])
        # p = _speckle_filter(p, jpy)
        # p = _terrain_correction(p)
        # p = _linear_to_from_db(p)
        # p = _to_int16(p, jpy)

        print("  [SNAP] Writing intermediate file...")
        # ProductIO.writeProduct(p, output_file, "GeoTiff")

    return outputs


def _apply_orbit_file(source, jpy):
    """Apply precise orbit file"""
    parameters = HashMap()
    parameters.put('continueOnFail', True)
    parameters.put('orbitType', 'Sentinel Precise (Auto Download)')
    parameters.put('polyDegree', jpy.get_type('java.lang.Integer')(3))

    return GPF.createProduct("Apply-Orbit-File", parameters, source)


def _thermal_noise_removal(source):
    """Remove thermal noise"""
    parameters = HashMap()
    parameters.put('reIntroduceThermalNoise', False)
    parameters.put('removeThermalNoise', True)

    return GPF.createProduct("ThermalNoiseRemoval", parameters, source)


def _remove_border_noise(source, jpy):
    """Remove GRD border noise"""
    parameters = HashMap()
    parameters.put('borderLimit', jpy.get_type('java.lang.Integer')(500))
    parameters.put('trimThreshold', 0.5)

    return GPF.createProduct("Remove-GRD-Border-Noise", parameters, source)


def _calibration(source, polar_list: list[str]):
    """Radiometric calibration"""
    parameters = HashMap()
    parameters.put('selectedPolarisations', ','.join(polar_list))
    source_bands = ['Intensity_' + band for band in polar_list]
    parameters.put('sourceBands', ','.join(source_bands))

    return GPF.createProduct("Calibration", parameters, source)


def _speckle_filter(source, jpy):
    """Apply speckle filter"""
    parameters = HashMap()
    java_integer = jpy.get_type('java.lang.Integer')

    parameters.put('filter', 'Refined Lee')
    parameters.put('dumpingFactor', java_integer(2))
    parameters.put('estimateENL', True)
    parameters.put('filterSizeX', java_integer(3))
    parameters.put('filterSizeY', java_integer(3))
    parameters.put('numLooksStr', '1')
    parameters.put('sigmaStr', '0.9')
    parameters.put('targetWindowSizeStr', '3x3')
    parameters.put('windowSize', '7x7')
    parameters.put('sourceBands', ','.join(list(source.getBandNames())))

    return GPF.createProduct("Speckle-Filter", parameters, source)


def _terrain_correction(source, map_projection='AUTO:42001'):
    """
    Terrain correction with DEM.

    Args:
        source: Input product
        map_projection: 'AUTO:42001' for auto UTM, 'WGS84(DD)' for WGS84 lat/lon
    """
    parameters = HashMap()
    parameters.put('auxFile', 'Latest Auxiliary File')
    parameters.put('demName', 'SRTM 1Sec HGT')
    parameters.put('demResamplingMethod', 'BILINEAR_INTERPOLATION')
    parameters.put('imgResamplingMethod', 'BILINEAR_INTERPOLATION')
    parameters.put('mapProjection', map_projection)
    parameters.put('nodataValueAtSea', False)
    parameters.put('pixelSpacingInMeter', 10.0)
    parameters.put('pixelSpacingInDegree', 8.983152841195215E-5)
    parameters.put('saveDEM', False)
    parameters.put('sourceBands', ','.join(list(source.getBandNames())))

    return GPF.createProduct("Terrain-Correction", parameters, source)


def _linear_to_from_db(source):
    """Convert linear to dB scale"""
    parameters = HashMap()
    source_bands = list(source.getBandNames())
    parameters.put('sourceBands', ','.join(source_bands))

    return GPF.createProduct("LinearToFromdB", parameters, source)


def _to_int16(source, jpy):
    """Convert bands to int16 (multiply by 100)"""
    source_bands = list(source.getBandNames())

    band_descriptor = jpy.get_type(
        'org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor'
    )
    target_bands = jpy.array(
        'org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor',
        len(source_bands),
    )

    for idx, source_band_name in enumerate(source_bands):
        target_band = band_descriptor()
        target_band.name = source_band_name
        target_band.type = 'int16'
        target_band.expression = "100 * " + source_band_name
        target_bands[idx] = target_band

    parameters = HashMap()
    parameters.put('targetBands', target_bands)
    return GPF.createProduct("BandMaths", parameters, source)


__all__ = ["preprocess", "output_files", "output_filenames"]

# def _remove_outer_border(tif_path, nodata_val=-32768):
#     """
#     去除外部边框（内存安全版）
#     """
#     if gdal is None or ogr is None:
#         return
#
#     try:
#         ds = gdal.Open(tif_path, gdal.GA_Update)
#         if not ds:
#             return
#
#         band = ds.GetRasterBand(1)
#         x_size, y_size = ds.RasterXSize, ds.RasterYSize
#
#         # 读取数据 (这里需要约 1.2GB 内存)
#         data = band.ReadAsArray()
#
#         # 【修改点 2】内存爆炸的核心修复
#         # 如果没有 numpy，就用原始方式（但可能会爆内存）
#         # 如果有 numpy，强制使用 uint8 (1字节) 而不是 int64 (8字节)
#         if np is not None:
#             # 使用 np.uint8，内存占用仅为原来的 1/8
#             mask_array = (data != 0).astype(np.uint8)
#         else:
#             # 只有在万不得已时才用这个，容易导致 MemoryError
#             mask_array = (data != 0) * 1
#
#             # 创建内存掩膜
#         drv_mem = gdal.GetDriverByName('MEM')
#         mask_ds = drv_mem.Create('', x_size, y_size, 1, gdal.GDT_Byte)
#         mask_ds.SetGeoTransform(ds.GetGeoTransform())
#         mask_ds.SetProjection(ds.GetProjection())
#         mask_ds.GetRasterBand(1).WriteArray(mask_array)
#
#         # 既然已经写入了 GDAL MEM，Python 里的 mask_array 就可以删了，释放内存
#         del mask_array
#
#         # 栅格转矢量
#         ogr_ds = ogr.GetDriverByName('Memory').CreateDataSource('mask_vec')
#         src_layer = ogr_ds.CreateLayer('src', srs=osr.SpatialReference(wkt=ds.GetProjection()))
#         fd = ogr.FieldDefn('PixelVal', ogr.OFTInteger)
#         src_layer.CreateField(fd)
#
#         gdal.Polygonize(mask_ds.GetRasterBand(1), mask_ds.GetRasterBand(1), src_layer, 0, [], callback=None)
#
#         # 提取外轮廓
#         filled_layer = ogr_ds.CreateLayer('filled', srs=osr.SpatialReference(wkt=ds.GetProjection()))
#
#         has_polygons = False
#         for feature in src_layer:
#             geom = feature.GetGeometryRef()
#             if not geom: continue
#
#             if geom.GetGeometryName() == 'MULTIPOLYGON':
#                 new_geom = ogr.Geometry(ogr.wkbMultiPolygon)
#                 for i in range(geom.GetGeometryCount()):
#                     poly = geom.GetGeometryRef(i)
#                     new_poly = ogr.Geometry(ogr.wkbPolygon)
#                     new_poly.AddGeometry(poly.GetGeometryRef(0))
#                     new_geom.AddGeometry(new_poly)
#             elif geom.GetGeometryName() == 'POLYGON':
#                 new_geom = ogr.Geometry(ogr.wkbPolygon)
#                 new_geom.AddGeometry(geom.GetGeometryRef(0))
#             else:
#                 continue
#
#             new_feat = ogr.Feature(filled_layer.GetLayerDefn())
#             new_feat.SetGeometry(new_geom)
#             filled_layer.CreateFeature(new_feat)
#             has_polygons = True
#
#         if not has_polygons:
#             print("  ⚠ Warning: No valid data found to process.")
#             ds = None
#             return
#
#         # 转回栅格掩膜
#         mask_ds.GetRasterBand(1).Fill(0)
#         gdal.RasterizeLayer(mask_ds, [1], filled_layer, burn_values=[1])
#
#         final_mask = mask_ds.GetRasterBand(1).ReadAsArray()
#
#         # 清理掉不再需要的对象
#         mask_ds = None
#         ogr_ds = None
#
#         # 应用修改：外部设为 NoData
#         data[(final_mask == 0)] = nodata_val
#
#         band.WriteArray(data)
#         band.SetNoDataValue(nodata_val)
#
#         ds.FlushCache()
#         ds = None
#         print("  ✓ Border removed successfully.")
#
#     except Exception as e:
#         print(f"  ⚠ Warning: Failed to remove outer border: {e}")
#
