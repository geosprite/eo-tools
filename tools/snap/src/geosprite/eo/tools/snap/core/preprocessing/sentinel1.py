# Copyright (c) GeoSprite. All rights reserved.
#
# Author: JH Zhang
#

"""
Sentinel-1 Preprocessing Module
Requires ESA SNAP with snappy Python bindings
"""

import os
from typing import List, Optional
try:
    import numpy as np
except ImportError:
    np = None
try:
    from osgeo import gdal, ogr, osr
except ImportError:
    gdal = None

try:
    from esa_snappy import ProductIO, GPF, HashMap, jpy
except ImportError as e:
    _SNAP_IMPORT_ERROR = e
    ProductIO = None
    GPF = None
    HashMap = None
    jpy = None
else:
    _SNAP_IMPORT_ERROR = None

__all__ = ["preprocess"]


def preprocess(
        input_file: str,
        polar_list: List[str],
        output_dir: Optional[str] = None,
        output_filename: Optional[str] = None
) -> List[str]:
    """
    Preprocess Sentinel-1 GRD data.

    Args:
        input_file: Path to Sentinel-1 .SAFE file or manifest.safe
        polar_list: List of polarizations to process (e.g., ['VV', 'VH'])
        output_dir: Output directory (default: same as input file)
        output_filename: Base output filename (default: auto-generated from input)

    Returns:
        List of output file paths

    Raises:
        ImportError: If esa_snappy is not available
        RuntimeError: If processing fails
    """
    if _SNAP_IMPORT_ERROR is not None:
        raise ImportError(
            "ESA SNAP snappy module is not installed. "
            "Please install SNAP and configure snappy Python bindings."
        ) from _SNAP_IMPORT_ERROR

    if output_dir:
        final_output_dir = output_dir
    else:
        final_output_dir = os.path.dirname(input_file)

    os.makedirs(final_output_dir, exist_ok=True)
    basename = os.path.basename(input_file).replace('.SAFE', '').replace('.safe', '')
    output_files = []

    for pol in polar_list:
        current_output_filename = os.path.join(final_output_dir, f"{basename}_{pol}.tif")
        temp_filename = current_output_filename.replace(".tif", "_temp.tif")

        print(f"Processing Sentinel-1 data:")
        print(f"  Input: {input_file}")
        print(f"  Polarization: {pol}")
        print(f"  Output: {current_output_filename}")

        if os.path.isfile(current_output_filename):
            print(f"  File already exists, skipping.")
            output_files.append(current_output_filename)
            continue

        print(f"  Starting processing pipeline...")

        # --- SNAP 处理链 ---
        p = ProductIO.readProduct(input_file)
        p = _apply_orbit_file(p, jpy)
        p = _thermal_noise_removal(p)
        p = _remove_border_noise(p, jpy)
        p = _calibration(p, [pol])
        p = _speckle_filter(p, jpy)
        p = _terrain_correction(p)
        p = _linear_to_from_dB(p)
        p = _bandmath_to_int16(p, jpy)

        print(f"  [SNAP] Writing intermediate file...")
        ProductIO.writeProduct(p, temp_filename, "GeoTiff")

        # --- 内存优化版去黑边 ---
        if gdal is not None:
            print(f"  [Preprocessing] Removing outer border artifacts...")
            _remove_outer_border(temp_filename)

            print(f"  [GDAL] Converting to COG (Compressed)...")
            try:
                ds = gdal.Open(temp_filename)
                src_nodata = ds.GetRasterBand(1).GetNoDataValue()

                # 【修改点 1】移除了不支持的 "ZLEVEL" 选项
                translate_options = gdal.TranslateOptions(
                    format="COG",
                    noData=src_nodata,
                    creationOptions=[
                        "COMPRESS=DEFLATE",
                        "PREDICTOR=2",
                        "BLOCKSIZE=512",
                        "OVERVIEWS=IGNORE_EXISTING",
                        "BIGTIFF=IF_NEEDED"
                    ]
                )
                gdal.Translate(current_output_filename, ds, options=translate_options)
                ds = None

                print(f"  ✓ COG Generated Successfully: {current_output_filename}")

                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            except Exception as e:
                print(f"  ⚠ GDAL Error during COG conversion: {e}")
                if os.path.exists(temp_filename):
                    if os.path.exists(current_output_filename):
                        os.remove(current_output_filename)
                    os.rename(temp_filename, current_output_filename)
        else:
            print(f"  ⚠ GDAL not installed. Saving uncompressed file.")
            os.rename(temp_filename, current_output_filename)

        output_files.append(current_output_filename)

    return output_files


def _remove_outer_border(tif_path, nodata_val=-32768):
    """
    去除外部边框（内存安全版）
    """
    if gdal is None or ogr is None:
        return

    try:
        ds = gdal.Open(tif_path, gdal.GA_Update)
        if not ds:
            return

        band = ds.GetRasterBand(1)
        x_size, y_size = ds.RasterXSize, ds.RasterYSize

        # 读取数据 (这里需要约 1.2GB 内存)
        data = band.ReadAsArray()

        # 【修改点 2】内存爆炸的核心修复
        # 如果没有 numpy，就用原始方式（但可能会爆内存）
        # 如果有 numpy，强制使用 uint8 (1字节) 而不是 int64 (8字节)
        if np is not None:
            # 使用 np.uint8，内存占用仅为原来的 1/8
            mask_array = (data != 0).astype(np.uint8)
        else:
            # 只有在万不得已时才用这个，容易导致 MemoryError
            mask_array = (data != 0) * 1

            # 创建内存掩膜
        drv_mem = gdal.GetDriverByName('MEM')
        mask_ds = drv_mem.Create('', x_size, y_size, 1, gdal.GDT_Byte)
        mask_ds.SetGeoTransform(ds.GetGeoTransform())
        mask_ds.SetProjection(ds.GetProjection())
        mask_ds.GetRasterBand(1).WriteArray(mask_array)

        # 既然已经写入了 GDAL MEM，Python 里的 mask_array 就可以删了，释放内存
        del mask_array

        # 栅格转矢量
        ogr_ds = ogr.GetDriverByName('Memory').CreateDataSource('mask_vec')
        src_layer = ogr_ds.CreateLayer('src', srs=osr.SpatialReference(wkt=ds.GetProjection()))
        fd = ogr.FieldDefn('PixelVal', ogr.OFTInteger)
        src_layer.CreateField(fd)

        gdal.Polygonize(mask_ds.GetRasterBand(1), mask_ds.GetRasterBand(1), src_layer, 0, [], callback=None)

        # 提取外轮廓
        filled_layer = ogr_ds.CreateLayer('filled', srs=osr.SpatialReference(wkt=ds.GetProjection()))

        has_polygons = False
        for feature in src_layer:
            geom = feature.GetGeometryRef()
            if not geom: continue

            if geom.GetGeometryName() == 'MULTIPOLYGON':
                new_geom = ogr.Geometry(ogr.wkbMultiPolygon)
                for i in range(geom.GetGeometryCount()):
                    poly = geom.GetGeometryRef(i)
                    new_poly = ogr.Geometry(ogr.wkbPolygon)
                    new_poly.AddGeometry(poly.GetGeometryRef(0))
                    new_geom.AddGeometry(new_poly)
            elif geom.GetGeometryName() == 'POLYGON':
                new_geom = ogr.Geometry(ogr.wkbPolygon)
                new_geom.AddGeometry(geom.GetGeometryRef(0))
            else:
                continue

            new_feat = ogr.Feature(filled_layer.GetLayerDefn())
            new_feat.SetGeometry(new_geom)
            filled_layer.CreateFeature(new_feat)
            has_polygons = True

        if not has_polygons:
            print("  ⚠ Warning: No valid data found to process.")
            ds = None
            return

        # 转回栅格掩膜
        mask_ds.GetRasterBand(1).Fill(0)
        gdal.RasterizeLayer(mask_ds, [1], filled_layer, burn_values=[1])

        final_mask = mask_ds.GetRasterBand(1).ReadAsArray()

        # 清理掉不再需要的对象
        mask_ds = None
        ogr_ds = None

        # 应用修改：外部设为 NoData
        data[(final_mask == 0)] = nodata_val

        band.WriteArray(data)
        band.SetNoDataValue(nodata_val)

        ds.FlushCache()
        ds = None
        print("  ✓ Border removed successfully.")

    except Exception as e:
        print(f"  ⚠ Warning: Failed to remove outer border: {e}")


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


def _calibration(source, polar_list: list):
    """Radiometric calibration"""
    parameters = HashMap()
    parameters.put('selectedPolarisations', ','.join(polar_list))
    parameters.put('sourceBands', ','.join(['Intensity_' + band for band in polar_list]))

    return GPF.createProduct("Calibration", parameters, source)


def _speckle_filter(source, jpy):
    """Apply speckle filter"""
    parameters = HashMap()
    JavaInteger = jpy.get_type('java.lang.Integer')

    parameters.put('filter', 'Refined Lee')
    parameters.put('dumpingFactor', JavaInteger(2))
    parameters.put('estimateENL', True)
    parameters.put('filterSizeX', JavaInteger(3))
    parameters.put('filterSizeY', JavaInteger(3))
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


def _linear_to_from_dB(source):
    """Convert linear to dB scale"""
    parameters = HashMap()
    sourceBands = list(source.getBandNames())
    parameters.put('sourceBands', ','.join(sourceBands))

    return GPF.createProduct("LinearToFromdB", parameters, source)


def _bandmath_to_int16(source, jpy):
    """Convert bands to int16 (multiply by 100)"""
    source_bands = list(source.getBandNames())

    BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    target_bands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', len(source_bands))

    for idx, sourceBand_name in enumerate(source_bands):
        targetBand = BandDescriptor()
        targetBand.name = sourceBand_name
        targetBand.type = 'int16'
        targetBand.expression = "100 * " + sourceBand_name
        target_bands[idx] = targetBand

    parameters = HashMap()
    parameters.put('targetBands', target_bands)
    return GPF.createProduct("BandMaths", parameters, source)
