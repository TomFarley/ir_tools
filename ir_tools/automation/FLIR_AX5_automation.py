#!/usr/bin/env python

"""


Created: 
"""

import logging, signal, time, datetime
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

from pynput.keyboard import Key, Controller
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
AUTOMATE_DAPROXY = True

FPATH_LOG = Path('protection.log')
TIME_REFRESH_MAIN_LOOP = 5  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_DELEY_PRESHOT = 105  # sec. PreShot comes ~2min before shot
TIME_RECORD_PRE_SHOT = 10  # sec. How long before shot is expected to start recording
TIME_DURATION_RECORD = 25  # sec. Duration of movie recording set in ResearchIR
TIME_DELAY_REARM = 120  # sec. Time to wait for clock train to finish.
TIME_TYPICAL_MIN_INTERSHOT = 3 * 60  # sec. Normally at least 3 min between shots
UPDATE_REMOTE_LOG_EVERY = 50  # loops. No point in updating this too often as Github pages site lag by ~20 min
STOP_TIME = datetime.time(20, 10)
PIXEL_COORDS_RECORD_WINDOW_1 = (1465, 55)  # Red record button (needs to be active)
PIXEL_COORDS_IMAGE_WINDOW_1 = (1465, 155)  # Click image to make window active for F5 record
BARS = '='*10

date = datetime.datetime.now().strftime('%Y-%m-%d')
path_export_px_today = (PATH_AUTO_EXPORT_PX_TAIL / '..' / date).resolve()

logger = logging.getLogger(__name__)
# logger.propagate = False
fhandler = logging.FileHandler(FPATH_LOG)
shandler = logging.StreamHandler()
[i.setLevel('INFO') for i in [logger, fhandler, shandler]]
formatter = logging.Formatter('%(asctime)s - %(message)s')
fhandler.setFormatter(formatter)
shandler.setFormatter(formatter)
logger.addHandler(fhandler)
logger.addHandler(shandler)

keyboard = Controller()

def sigint_handler(proc_da_proxy):
    def _sigint_handler(sig, frame):
        logger.info('>>> CTRL+C <<<')
        daproxy.kill_da_proxy(proc_da_proxy)
        raise KeyboardInterrupt
    return _sigint_handler

def update_state_and_shot(FPATH_MSG_LOG, shot_prev, state_prev, times):
    modified_da_log, t_mod_da_log = ir_automation.file_updated(FPATH_MSG_LOG, t_mod_prev=times['mod_da_log'])
    times['mod_da_log'] = t_mod_da_log
    if modified_da_log:
        shot, state = get_shot(fn=FPATH_MSG_LOG), get_state(fn=FPATH_MSG_LOG)
        t_state_change = datetime.datetime.now()
        times['state_change'] = t_state_change
        times[state] = t_state_change

        if shot != shot_prev:
            logger.info(f'{BARS} Shot number changed to {shot}. State: "{state}" {BARS}')

        # if state in ('Ready', 'PreShot', 'Trigger', 'Abort'):
        logger.info(f'Entered state "{state}" for shot {shot}')

        shot_time_estimate, delay = daproxy.update_estimated_shot_time(state, t_state_change, times.get('shot_expected'))
        times['shot_expected'] = shot_time_estimate

        if shot_time_estimate is not None:
            times['finish_recording'] = times['shot_expected'] + datetime.timedelta(seconds=TIME_DURATION_RECORD+2)
            times['re-arm'] = times['shot_expected'] + datetime.timedelta(seconds=TIME_DELAY_REARM)
    else:
        state = state_prev
        shot = shot_prev

    return shot, state, times

def start_protection_camera_recording(pixel_coords):
    logger.info(f'Clicking on image and pressing F5 to start recording')
    ir_automation.click(*pixel_coords)
    keyboard.press(Key.ctrl)  # Display mouse location 
    keyboard.release(Key.ctrl)
    keyboard.press(Key.f5)

def organise_new_movie_file(path_auto_export, fn_format_movie, shot, path_export_today, n_file_prev):
    fns_autosaved = ir_automation.filenames_in_dir(path_auto_export)
    i_order_fns, ages_fns, fns_sorted = ir_automation.sort_files_by_age(fns_autosaved, path=path_auto_export)
    n_files = len(fns_sorted)

    saved_shots = ir_automation.shot_nos_from_fns(fns_sorted, pattern=fn_format_movie.format(shot='(\d+)'))
    if n_files == n_file_prev:
        logger.warning(f'Number of files, {n_files}, has not changed after shot!')

    if n_files > 0:
        fn_new, age_fn_new, shot_fn_new = Path(fns_sorted[0]), ages_fns[0], saved_shots[0]
        path_fn_new = path_auto_export / fn_new
        logger.info(f'File "{fn_new}" for shot {shot_fn_new} ({shot} expected) saved {age_fn_new:0.1f} s ago')
        if (shot_fn_new != shot) and (age_fn_new < TIME_TYPICAL_MIN_INTERSHOT):
            fn_expected = fn_format_movie.format(shot=f'0{shot}')
            path_fn_expected = path_auto_export / fn_expected
            if not path_fn_expected.is_file():
                logger.info(f'Renaming latest file from "{path_fn_new.name}" to "{path_fn_expected.name}"')
                path_fn_new.rename(path_fn_expected)
                path_fn_new = path_fn_expected
                if not path_fn_expected.is_file():
                    logger.warning(f'File rename failed')
            else:
                logger.warning(f'Expected shot no file already exists: {path_fn_expected.name}. '
                               f'Not sure how to rename {fn_new}\nPulses saved: {saved_pulses}')
        if path_fn_new.is_file():
            dest = path_export_today / path_fn_new.name
            dest.write_bytes(path_fn_new.read_bytes())  # for binary files
            logger.info(f'Wrote new movie file to {dest}')
        else:
            logger.warning(f'New file does not exist: {path_fn_new}')
    return n_files

def automate_ax5_camera_researchir():
    logger.info('Starting camera automation')
    if AUTOMATE_DAPROXY:
        proc_da_proxy = daproxy.run_da_proxy(FPATH_DA_PROXY)
    else:
        proc_da_proxy = None

    signal.signal(signal.SIGINT, sigint_handler(proc_da_proxy))

    if FPATH_MSG_LOG.is_file():
        logger.info(f'Watching daproxy log file: {FPATH_MSG_LOG}')
    else:
        raise FileNotFoundError(f'DAProxy log file doesn not exist: {FPATH_MSG_LOG}')

    shot, state = get_shot(fn=FPATH_MSG_LOG, logger=logger), get_state(fn=FPATH_MSG_LOG, logger=logger)
    logger.info(f'{BARS} Ready for shot {shot+1} in state "{state}" {BARS}')

    times = dict(mod_da_log=None, t_state_change=None)
    loop_cnt = 0
    n_files = 0
    recording = False

    while True:

        shot, state, times = update_state_and_shot(FPATH_MSG_LOG, shot, state, times)
        
        t_now = datetime.datetime.now()
        # print(f'times: {times}')
        # print(f't_now: {t_now}')
        # logger.info(f't_shot_expected: {times.get("shot_expected")}')
        dt = (times['shot_expected'] - t_now).total_seconds() if ('PreShot' in times) else None

        if (dt is not None) and (dt >= 0):
            logger.info(f'Shot expected in dt: {dt} s')
            if (dt <= TIME_RECORD_PRE_SHOT) and (not recording):
                start_protection_camera_recording(PIXEL_COORDS_IMAGE_WINDOW_1)
                recording = True
                # time.sleep(TIME_DURATION_RECORD+5)                    
    
            dt = (times['finish_recording'] - t_now).total_seconds() if ('PreShot' in times) else None
            if (dt is not None) and (dt >= 0):
                logger.info(f'Recording should finish in dt: {dt} s')

        if (dt is not None) and (dt <= 0) and (recording):
            recording = False
            n_files = organise_new_movie_file(PATH_AUTO_EXPORT_PX_TAIL, FN_FORMAT_MOVIE, shot, path_export_px_today, n_file_prev=n_files)

        if t_now.time() > STOP_TIME:
            if AUTOMATE_DAPROXY:
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