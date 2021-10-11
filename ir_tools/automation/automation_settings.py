#!/usr/bin/env python

"""


Created: 
"""
import datetime
import logging
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

_FREIA_HOME_PATH_OPTIONS = ['\\\\samba-1.hpc.l\\home\\', '\\\\samba-2.hpc.l\\home\\', 'H:\\\\home\\', 'F:\\\\home\\',
                            '\\\\samba-1.hpc.l\\', '\\\\samba-2.hpc.l\\', 'H:\\\\', 'F:\\\\']

for option in _FREIA_HOME_PATH_OPTIONS:
    FREIA_HOME_PATH = Path(option)
    data_path = FREIA_HOME_PATH / 'data'
    if data_path.is_dir():
        logger.info(f'Freia mapping located at: {FREIA_HOME_PATH}')
        break
else:
    logger.warning('Cannot locate Freia mapping')
    print(f'Cannot locate Freia mapping among: {_FREIA_HOME_PATH_OPTIONS}')

PATHS_AUTO_EXPORT = {'LWIR1': Path('D:\\MAST-U\\LWIR_IRCAM1_HM04-A\\Operations\\2021-1st_campaign\\auto_export\\'),
                     'MWIR1': Path('D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export\\'),
                     'Px_protection': Path('D:\\FLIR_AX5_Protection_data\\PX Coil Tail\\auto_export\\'),
                     'SW_beam_dump': Path('D:\\FLIR_AX5_Protection_data\\SW_beam_dump\\auto_export\\')}
PATH_T_DRIVE = Path(f'T:\\tfarley\\RIR\\')
PATHS_FREIA_EXPORT = {
                      'MWIR1': Path(f'{FREIA_HOME_PATH}\\data\\movies\\diagnostic_pc_transfer\\rir\\'),  #
                      'LWIR1': Path(f'{FREIA_HOME_PATH}\\data\\movies\\diagnostic_pc_transfer\\rit\\')}
FNS_FORMAT_MOVIE = {'LWIR1': '{shot}.RAW',
                    'MWIR1': '{shot}.ats',
                    'Px_protection': '{shot}.seq',  # shot=(\d+) for regex match
                    'SW_beam_dump': '{shot}.seq'}
AUTOMATE_DAPROXY = True
TIME_REFRESH_MAIN_LOOP_OPS = 25  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_REFRESH_MAIN_LOOP_PRESHOT = 1  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_REFRESH_MAIN_LOOP_NON_OPS = 10*60  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_DELEY_PRESHOT = 105  # sec. PreShot comes ~2min before shot
TIME_RECORD_PRE_SHOT = 6  # sec. How long before shot is expected to start recording
TIME_DURATION_RECORD = 15  # sec. Duration of protection movie recording set in ResearchIR
TIME_DELAY_REARM = 120  # sec. Time to wait for clock train to finish.
TIME_TYPICAL_MIN_INTERSHOT = 3 * 60  # sec. Normally at least 3 min between shots
LOOP_COUNT_UPDATE = 8  # loops. No point in updating this too often as Github pages site lag by ~20 min
STOP_TIME = datetime.time(20, 10)
START_TIME = datetime.time(7, 50)
PIXEL_COORDS_IMAGE = {'LWIR1': (500, 766),  # Record button
                      'MWIR1': (360, 155),  # Top left window, record button at (360, 55)
                      'Px_protection': (1465, 155),  # Top right window
                      'SW_beam_dump': (1465, 955)}  # Bottom right window
BARS = '='*10
IRCAM_CAMERAS = ['LWIR1', 'LWIR2', 'MWIR3']
FLIR_CAMERAS = ['MWIR1', 'MWIR2']
PROTECTION_CAMERAS = ['Px_protection', 'SW_beam_dump']
FPATH_LOG = Path('IR_automation.log')
YES = '✓'
NO = '✕'
PATH_HDD_OUT = Path(r'D:\\MAST-U\LWIR_IRCAM1_HM04-A\Operations\To_be_exported')