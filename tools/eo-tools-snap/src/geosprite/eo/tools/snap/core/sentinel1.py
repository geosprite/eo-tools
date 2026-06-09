# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""
Sentinel-1 Preprocessing Module
Requires ESA SNAP with snappy Python bindings
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from geosprite.eo.io.raster import convert_to_cog

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
    if _SNAP_IMPORT_ERROR is not None:
        raise ImportError(
            "ESA SNAP snappy module is not installed. "
            "Please install SNAP and configure snappy Python bindings."
        ) from _SNAP_IMPORT_ERROR

    resolved_dir = os.path.abspath(output_dir)
    os.makedirs(resolved_dir, exist_ok=True)
    prefix: str = "iw-"

    outputs = [
        os.path.join(resolved_dir, prefix + pol.lower() + ".tif")
        for pol in polar_list
    ]

    for pol, output_file in zip(polar_list, outputs):
        print("Processing Sentinel-1 data:")
        print(f"  Input: {input_file}")
        print(f"  Polarization: {pol}")
        print(f"  Output: {output_file}")

        if os.path.isfile(output_file):
            print("  File already exists, skipping.")
            continue

        print("  Starting processing pipeline...")

        p = ProductIO.readProduct(input_file)
        p = _apply_orbit_file(p, jpy)
        p = _thermal_noise_removal(p)
        p = _remove_border_noise(p, jpy)
        p = _calibration(p, [pol])
        p = _speckle_filter(p, jpy)
        p = _terrain_correction(p)
        p = _linear_to_from_db(p)
        p = _to_int16(p, jpy)

        output_path = Path(output_file)

        with TemporaryDirectory(
            prefix="geosprite-snap-s1-",
            dir=str(output_path.parent),
        ) as temp_dir:
            intermediate_file = Path(temp_dir) / output_path.name
            print("  [SNAP] Writing intermediate GeoTIFF...")
            ProductIO.writeProduct(p, str(intermediate_file), "GeoTiff")
            print("  [GDAL] Translating GeoTIFF to COG...")
            convert_to_cog(str(intermediate_file), output_file)

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


__all__ = ["preprocess"]
