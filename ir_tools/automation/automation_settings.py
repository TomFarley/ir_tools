#!/usr/bin/env python

"""


Created: 
"""
import datetime, os, logging, socket
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

HOST = socket.gethostname().upper()

# ==================== Check these settings for current camera setup ====================

# Set which cameras are run from each control PC here
ACTIVE_CAMERAS_FOR_HOST = {
    'MWIR-PC1':
        # active_cameras = {'LWIR1': False, 'MWIR1': True, 'Px_protection': True, 'SW_beam_dump': False}
        {'LWIR1': False, 'MWIR1': True, 'Px_protection': True, 'SW_beam_dump': True},
     'H0012':
        {'LWIR1': True, 'MWIR1': False, 'Px_protection': False, 'SW_beam_dump': False}
    }

# Set pixel coordinates corresponding to current window layout
PIXEL_COORDS_IMAGE = {'LWIR1': (500, 766),  # Record button
                      'MWIR1': (360, 95),  # Top left window, record button at (360, 55)
                      'Px_protection': (1465, 95),  # Top right window
                      'SW_beam_dump': (1465, 645)}  # Bottom right window, record button at (1465, 615)

# Set True to try to launch DAproxy process from python
AUTOMATE_DAPROXY = False

# =========================================================================================

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
REMOTE_LOG_FILES = {'H0012': 'D:\\ir_log\\LWIR1.md',
                    'MWIR-PC1': 'D:\\ir_log\\MWIR1.md'}
TIME_REFRESH_MAIN_LOOP_OPS = 25  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_REFRESH_MAIN_LOOP_PRESHOT = 1  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_REFRESH_MAIN_LOOP_NON_OPS = 10*60  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_DELEY_PRESHOT = 105  # sec. PreShot comes ~2min before shot
TIME_RECORD_PRE_SHOT = 6  # sec. How long before shot is expected to start recording
TIME_DURATION_RECORD = 15  # sec. Duration of protection movie recording set in ResearchIR
TIME_DELAY_REARM = 120  # sec. Time to wait for clock train to finish.
TIME_TYPICAL_MIN_INTERSHOT = 3 * 60  # sec. Normally at least 3 min between shots
LOOP_COUNT_UPDATE = 10  # loops. No point in updating this too often as Github pages site lag by ~20 min
TIME_STOP_OPS = datetime.time(20, 15)
TIME_STOP_EARLY_ARM = datetime.time(18, 45)  # Stop arming (FLIR) camera after shot in evening to prevent morning freeze
TIME_START_OPS = datetime.time(7, 50)

BARS = '='*10
IRCAM_CAMERAS = ['LWIR1', 'LWIR2', 'MWIR3']
FLIR_CAMERAS = ['MWIR1', 'MWIR2']
PROTECTION_CAMERAS = ['Px_protection', 'SW_beam_dump']
FPATH_LOG = Path(f'D:\\ir_tools\\ir_tools\\automation\\log\\IR_automation_{HOST}.log')
YES = '✓'
NO = '✕'
PATH_HDD_OUT = Path(r'D:\\MAST-U\LWIR_IRCAM1_HM04-A\Operations\To_be_exported')