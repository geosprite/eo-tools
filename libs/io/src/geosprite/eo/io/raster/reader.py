# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from dataclasses import dataclass
from typing import Tuple, List, Optional, Union

import numpy as np

from .dataset import RasterDataset, RasterProfile, SlidingWindow

@dataclass
class RasterSource:
    """Represents a raster file with its path, original size, and read scale."""
    path: str
    size: Tuple[int, int]
    scale: Tuple[float, float]

    @staticmethod
    def from_profile(path: str, raster_size: Tuple[int, int], profile: RasterProfile) -> "RasterSource":
        """Create a RasterSource instance scaled to match the given profile."""
        raster = RasterSource(path=path, size=raster_size, scale=(1.0, 1.0))
        return raster.rescale(profile)

    def rescale(self, profile: RasterProfile) -> "RasterSource":
        """Re-compute scale factors based on a new profile."""
        scale = (profile.height / self.size[0], profile.width / self.size[1])
        return RasterSource(self.path, self.size, scale)


class DatasetReader:
    """
    Reads and combines multiple raster datasets with optional sliding-window iteration.
    """

    def __init__(
            self,
            *filepaths: str,
            window_size: Optional[Union[int, Tuple[int, int]]] = None
    ):
        if len(filepaths) == 0:
            raise ValueError("At least one image is required")

        self.profile: Optional[RasterProfile] = None

        # Initialize profile and files
        self.files: List[RasterSource] = self._init_files(filepaths)

        # Initialize sliding windows for block-based reading/writing
        if window_size is not None:
            raster_shape = (self.profile.height, self.profile.width)
            self.windows = SlidingWindow(raster_shape, window_size)
        else:
            self.windows = None

    def combine(self, *filepaths):
        """Add more files and re-compute scales to match the largest profile."""
        files = self._init_files(filepaths)
        self._update_windows(self.profile)
        self.files = [file.rescale(self.profile) for file in self.files]
        self.files.extend(files)

    def read(self,
             window: Optional[Tuple[int, int, int, int]] = None,
             window_buffer_size: Optional[int] = None,
             nodata_to_nan: bool = False) -> np.ndarray:
        """
        Read data from all files, optionally within a buffered window.
        """
        if isinstance(window, tuple) and len(window) == 4:
            if isinstance(window_buffer_size, int):
                window = SlidingWindow.buffer(window, (self.profile.height, self.profile.width), window_buffer_size)
        else:
            window = 0, 0, self.profile.height, self.profile.width

        data = []
        for raster in self.files:
            with RasterDataset(raster.path) as dataset:
                data.append(dataset.read(window=window, scale=raster.scale, nodata_to_nan=nodata_to_nan))

        return np.asarray(data)

    def read_as_8bit(self,
                     window: Optional[Tuple[int, int, int, int]] = None,
                     lower_percent: Optional[int] = None,
                     upper_percent: Optional[int] = None) -> np.ndarray:
        """
        Read data from all files and stretch to 8-bit (0-255).
        """
        if not isinstance(window, tuple) or len(window) != 4:
            window = 0, 0, self.profile.height, self.profile.width

        data = []
        for raster in self.files:
            with RasterDataset(raster.path) as dataset:
                data.append(dataset.read_as_8bit(
                    window=window, scale=raster.scale,
                    lower_percent=lower_percent, upper_percent=upper_percent
                ))

        return np.asarray(data)

    def __iter__(self):
        return self

    def __next__(self) -> Tuple[int, int, int, int]:
        if not self.windows:
            raise StopIteration

        window = next(self.windows)
        if window is None:
            raise StopIteration

        return window

    def _init_files(self, filepaths) -> List[RasterSource]:
        """Update profiles due to the new files and create RasterSource instances."""
        file_profiles = [self._update_profile(filepath) for filepath in filepaths]

        return [RasterSource.from_profile(filepath, (fp.height, fp.width), self.profile)
                for filepath, fp in zip(filepaths, file_profiles)]

    def _update_profile(self, filepath: str) -> RasterProfile:
        """Validate spatial reference consistency and keep the largest profile."""
        with RasterDataset(filepath) as dataset:
            file_profile = dataset.profile

        if isinstance(self.profile, RasterProfile):
            if not file_profile.spatial_ref.IsSame(self.profile.spatial_ref):
                raise ValueError(
                    f"Spatial reference of raster '{filepath}' differs and cannot be combined."
                )

            if self.profile.height < file_profile.height or self.profile.width < file_profile.width:
                self.profile = file_profile
        else:
            self.profile = file_profile

        return file_profile

    def _update_windows(self, profile: RasterProfile) -> None:
        """Re-create windows when the profile changes."""
        if self.windows is not None:
            raster_shape = (profile.height, profile.width)
            window_shape = (self.windows.height, self.windows.width)
            self.windows = SlidingWindow(raster_shape, window_shape)

