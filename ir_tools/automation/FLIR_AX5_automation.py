#!/usr/bin/env python

"""


Created: 
"""

import logging, signal, time, datetime
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from ir_tools.automation import ir_automation, daproxy
from ir_tools.automation.daproxy import FPATH_DA_PROXY, FPATH_MSG_LOG, get_shot, get_state

PATH_AUTO_EXPORT_PX_TAIL = Path(f'D:\\FLIR_AX5_Protection_data\\PX Coil Tail\\auto_export')
PATH_T_DRIVE = Path(f'T:\\tfarley\\RIR\\')
PATH_FREIA = Path('H:\\data\\movies\\diagnostic_pc_transfer\\rir\\')

FN_FORMAT_MOVIE = '{shot}.seq'  # shot=(\d+) for regex match

FPATH_LOG = Path('protection.log')
TIME_REFRESH_MAIN_LOOP = 5  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_DELEY_ARM_PRESHOT = 110  # sec. PreShot comes ~2min before shot
TIME_DURATION_RECORD = 25  # sec. Duration of movie recording set in ResearchIR
TIME_TYPICAL_MIN_INTERSHOT = 3 * 60  # sec. Normally at least 3 min between shots
UPDATE_REMOTE_LOG_EVERY = 50  # loops. No point in updating this too often as Github pages site lag by ~20 min
STOP_TIME = datetime.time(20, 10)
PIXEL_COORDS_RECORD_WINDOW_1 = (360*3, 55)

date = datetime.now().strftime('%Y-%m-%d')
path_export_px_today = PATH_AUTO_EXPORT_PX_TAIL / date

logger = logging.getLogger(__name__)
# logger.propagate = False
handler = logging.FileHandler(FPATH_LOG)
[i.setLevel('INFO') for i in [logger, handler]]
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def sigint_handler(proc_da_proxy):
    def _sigint_handler(sig, frame):
        logger.info('>>> CTRL+C <<<')
        daproxy.kill_da_proxy(proc_da_proxy)
        raise KeyboardInterrupt
    return _sigint_handler

def automate_ax5_camera_researchir():
    proc_da_proxy = daproxy.run_da_proxy(FPATH_DA_PROXY)

    signal.signal(signal.SIGINT, sigint_handler(proc_da_proxy))

    t_mod_da_log = None

    loop_cnt = 0
    n_files = 0
    while True:
        modified_da_log, t_mod_da_log = ir_automation.file_updated(FPATH_MSG_LOG, t_mod_prev=t_mod_da_log)
        if modified_da_log:
            shot, state = get_shot(logger=logger), get_state(logger=logger)

        if state == 'Ready':
            logger.info(f'Entered state "{state}" for shot {shot}')

        if state == 'PreShot':
            logger.info(f'Entered state "{state}" for shot {shot}. '
                        f'Waiting {TIME_DELEY_ARM_PRESHOT} s to start recording')
            time.sleep(TIME_DELEY_ARM_PRESHOT)

        if state in ('PreShot', 'Trigger'):
            logger.info(f'In state "{state}" for shot {shot}')
            logger.info(f'Started recording')
            ir_automation.click(*PIXEL_COORDS_RECORD_WINDOW_1)
            time.sleep(TIME_DURATION_RECORD+5)

            i_order_fns, ages_fns, fns_sorted = ir_automation.sort_files_by_age(path_export_px_today)
            saved_shots = ir_automation.shot_nos_from_fns(fns_sorted, pattern=FN_FORMAT_MOVIE.format(shot='(\d+)'))
            if len(fns_sorted) == n_files:
                logger.warning(f'Number of files, {n_files}, has not changed after shot!')

            n_files = len(fns_sorted)
            if n_files > 0:
                fn_new, age_fn_new, shot_fn_new = Path(fns_sorted[0]), ages_fns[0], saved_shots[0]
                logger.info(f'File "{fn_new}" for shot {shot_fn_new} ({shot} expected) saved {age_fn_new:0.1f} s ago')
                if (shot_fn_new != shot) and (age_fn_new < TIME_TYPICAL_MIN_INTERSHOT):
                    if shot_fn_new != shot:
                        fn_expected = PATH_AUTO_EXPORT_PX_TAIL / FN_FORMAT_MOVIE.format(shot=shot)
                        if not fn_expected.is_file():
                            logger.info(f'Renaming latest file from "{fn_new.name}" to "{fn_expected.name}"')
                            (PATH_AUTO_EXPORT_PX_TAIL / fn_new).rename(fn_expected)
                        else:
                            logger.warning(f'Expected shot no file already exists: {fn_expected}. '
                                           f'Not sure how to rename {fn_new}\nPulses saved: {saved_pulses}')

        if state == 'Abort':
            logger.info(f'Entered state "{state}" for shot {shot}')

        if datetime.datetime.now().time() > STOP_TIME:
            daproxy.kill_da_proxy(proc_da_proxy)
            logger.info('>>> GOODNIGHT <<<')
            break
        elif loop_cnt % UPDATE_REMOTE_LOG_EVERY == 0:
            pass
            # update_remote_log(logger=logger)

        loop_cnt += 1
        time.sleep(TIME_REFRESH_MAIN_LOOP)

if __name__ == '__main__':
    automate_ax5_camera_researchir()
    pass