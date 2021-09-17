#!/usr/bin/env python

"""


Created: 
"""

import logging, re
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path
from copy import copy

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
logger.propagate = False

class IrCalibrationDataset:
    directory_keys_below = ['date', 'filter', 'lens', 'window', 't_int']
    directory_keys_above = ['camera', ]
    filename_keys = ['T']
    ascii_image_extensions = ['asc', 'ASC']
    file_patterns = ['(?P<T>\d+\.?\d*)C?_(?P<n_frame_av>\d+)av(?P<fn_ext>\.'+'|.'.join(ascii_image_extensions)+')']
    col_types = {'t_int': float, 'T': float}

    columns = ['file']

    def __init__(self):
        self._info = {}
        self.file_keys = self.directory_keys_above + self.directory_keys_below + self.filename_keys
        df = pd.DataFrame(columns=self.file_keys + self.columns)
        df = df.astype(self.col_types)
        df = df.set_index(self.file_keys)
        self.df = df
        pass

    def read_calibration_directory(self, path):
        path = Path(path)

        info = self._info
        if len(self.directory_keys_above) > 0:
            info[self.directory_keys_above[0]] = str(path.name)
            path_prev = path
            for dir_above in self.directory_keys_above[1:]:
                path_prev = path_prev.parent
                info[dir_above] = str(path_prev.name)

        self._extract_path_info(path, directory_levels=self.directory_keys_below)

        print(self.df)


    def _extract_path_info(self, path, directory_levels):
        info = self._info

        levels = self.file_keys
        df = self.df
        for item in path.iterdir():
            if item.is_dir():
                value = str(item.name).replace('ms', '')
                info[directory_levels[0]] = value
                self._extract_path_info(item, directory_levels[1:])
            elif item.is_file() and (len(directory_levels) == 0):
                for pattern in self.file_patterns:
                    fn = item.name
                    m = re.match(pattern, fn)
                    if m:
                        info.update(m.groupdict())
                        keys = tuple(info[key] for key in levels)
                        try:
                            df.loc[keys, 'file'] = item.name
                            df.loc[keys, 'path'] = item.parent
                        except KeyError as e:
                            logger.warning(f'Failed to add file "{item}": {e}')
                        else:
                            logger.info(f'Added {item} for {keys}')
                        for key, value in m.groupdict().items():
                            if key not in levels:
                                try:
                                    df.loc[keys, key] = value
                                except Exception as e:
                                    logger.warning(f'Failed to add additional col from filename "{key}"={value}: {e}')
                        self._keys_default = dict(zip(self.file_keys, keys))
                    else:
                        logger.info(f'Ignoring file {item}. File extension not in {self.ascii_image_extensions}')

    def read_image(self, keys: dict):
        keys_image = copy(self._keys_default)
        keys_image.update(keys)
        keys_image = tuple(keys_image.values())

        row = self.df.loc[keys_image, :]
        path_fn = row['path'] / row['file']


        raise NotImplementedError
        return image


if __name__ == '__main__':
    # path = f'/home/tfarley/repos/ir_tools/ir_tools/calibration/BB_calibration_data/2021-08-02/FLIR_SC7500-65800047/'
    # path = f'/home/tfarley/repos/ir_tools/ir_tools/calibration/BB_calibration_data/FLIR_SC7500-65800047/'
    path = f'/home/tfarley/repos/ir_tools/ir_tools/calibration/BB_calibration_data/IRCAM_Velox_L_0101A18CH/'
    data = IrCalibrationDataset()
    data.read_calibration_directory(path)
    image = data.read_image({})
    pass