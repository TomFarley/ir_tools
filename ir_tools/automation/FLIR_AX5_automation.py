#!/usr/bin/env python

"""


Created: 
"""

import logging, signal, time, datetime, os
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

from pynput.keyboard import Key, Controller
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from ir_tools.automation import ir_automation, daproxy
from ir_tools.automation.daproxy import FPATH_DA_PROXY, FPATH_MSG_LOG, get_shot, get_state
from ir_tools.automation.ir_automation import make_iterable

PATHS_AUTO_EXPORT = {'LWIR1': Path('D:\\MAST-U\\LWIR_IRCAM1_HM04-A\\Operations\\2021-1st_campaign\\auto_export\\'),
                     'MWIR1': Path('D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export\\'),
                     'Px_protection': Path('D:\\FLIR_AX5_Protection_data\\PX Coil Tail\\auto_export\\'),
                     'SW_beam_dump': Path('D:\\FLIR_AX5_Protection_data\\SW_beam_dump\\auto_export\\')}
PATH_T_DRIVE = Path(f'T:\\tfarley\\RIR\\')
PATH_FREIA = Path('H:\\data\\movies\\diagnostic_pc_transfer\\rir\\')

FNS_FORMAT_MOVIE = {'LWIR1': '{shot}.RAW',
                    'MWIR1': '{shot}.ats',
                    'Px_protection': '{shot}.seq',  # shot=(\d+) for regex match
                    'SW_beam_dump': '{shot}.seq'}

AUTOMATE_DAPROXY = False

FPATH_LOG = Path('MWIR1_pc.log')

TIME_REFRESH_MAIN_LOOP_OPS = 5  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_REFRESH_MAIN_LOOP_NON_OPS = 10*60  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_DELEY_PRESHOT = 105  # sec. PreShot comes ~2min before shot
TIME_RECORD_PRE_SHOT = 10  # sec. How long before shot is expected to start recording
TIME_DURATION_RECORD = 25  # sec. Duration of movie recording set in ResearchIR
TIME_DELAY_REARM = 120  # sec. Time to wait for clock train to finish.
TIME_TYPICAL_MIN_INTERSHOT = 3 * 60  # sec. Normally at least 3 min between shots
LOOP_COUNT_UPDATE = 50  # loops. No point in updating this too often as Github pages site lag by ~20 min
STOP_TIME = datetime.time(20, 10)
START_TIME = datetime.time(7, 50)
PIXEL_COORDS_RECORD_WINDOW_1 = (1465, 55)  # Red record button (needs to be active)
PIXEL_COORDS_IMAGE_WINDOW_1 = (1465, 155)  # Click image to make window active for F5 record
PIXEL_COORDS_IMAGE = {'LWIR1': (580, 766),  # Record button
                      'MWIR1': (360, 155),  # Top left window, record button at (360, 55)
                      'Px_protection': (1465, 155),  # Top right window
                      'SW_beam_dump': (1465, 955)}  # Bottom right window
BARS = '='*10

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

def empty_auto_export(path_auto_export):
    path_auto_export_backup = (path_auto_export / '..' / 'auto_export_backup').resolve()
    ir_automation.mkdir(path_auto_export_backup)
    ir_automation.copy_files(path_auto_export, path_auto_export_backup)
    ir_automation.delete_files_in_dir(path_auto_export, glob='*.RAW')
    logger.info(f'Moved previously exported files to {path_auto_export_backup} from {path_auto_export}')

def check_date(auto_export_paths):
    date = datetime.datetime.now()
    date_str = date.strftime('%Y-%m-%d')
    paths_today = dict()
    if date.weekday() <= 5:
        # No weekend ops
        for camera, path in auto_export_paths.items():
            path_export_today = (path / '..' / date_str).resolve()
            success, created = ir_automation.mkdir(path_export_today)
            paths_today[camera] = path_export_today
            if created:
                empty_auto_export(path)

    return date_str, paths_today

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
        state_updated = True
        if (shot != shot_prev):
            shot_updated = True
            times['shot_change'] = t_state_change
        else:
            shot_updated = False
    else:
        state = state_prev
        shot = shot_prev
        state_updated = False
        shot_updated = False

    return shot, state, times, shot_updated, state_updated

def start_recording_research_ir(pixel_coords, camera):
    logger.info(f'Clicking on image and pressing F5 to start recording for "{camera}" camera')
    ir_automation.click(*pixel_coords)
    keyboard.press(Key.ctrl)  # Display mouse location 
    keyboard.release(Key.ctrl)
    keyboard.press(Key.f5)

def organise_new_movie_file(path_auto_export, fn_format_movie, shot, path_export_today, n_file_prev, t_shot_change):
    fns_autosaved = ir_automation.filenames_in_dir(path_auto_export)
    fns_sorted, i_order, t_mod, ages, ages_sec = ir_automation.sort_files_by_age(fns_autosaved, path=path_auto_export)
    n_files = len(fns_sorted)

    saved_shots = ir_automation.shot_nos_from_fns(fns_sorted, pattern=fn_format_movie.format(shot='(\d+)'))
    if n_files == n_file_prev:
        logger.warning(f'Number of files, {n_files}, has not changed after shot!')

    if n_files > 0:
        fn_new, age_fn_new, shot_fn_new = Path(fns_sorted[0]), ages[0], saved_shots[0]
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
    host = os.environ['COMPUTERNAME']
    # TODO: Set with argpass?
    if host == 'MWIR-PC1':
        active_cameras = {'LWIR1': False, 'MWIR1': True, 'Px_protection': True, 'SW_beam_dump': False}
    else:
        active_cameras = {'LWIR1': True, 'MWIR1': False, 'Px_protection': False, 'SW_beam_dump': False}

    logger.info(f'Starting camera automation on {host} PC for cameras: {", ".join([camera for camera, active in active_cameras.items() if active])}')
    
    if AUTOMATE_DAPROXY:
        proc_da_proxy = daproxy.run_da_proxy(FPATH_DA_PROXY)
    else:
        proc_da_proxy = None

    signal.signal(signal.SIGINT, sigint_handler(proc_da_proxy))

    if FPATH_MSG_LOG.is_file():
        logger.info(f'Watching daproxy log file: {FPATH_MSG_LOG}')
    else:
        raise FileNotFoundError(f'DAProxy log file doesn not exist: {FPATH_MSG_LOG}')

    shot, state = get_shot(fn=FPATH_MSG_LOG), get_state(fn=FPATH_MSG_LOG)
    logger.info(f'{BARS} Ready for shot {shot+1} in state "{state}" {BARS}')

    auto_export_paths = {}
    for camera, active in active_cameras.items():
        if active:
            auto_export_paths[camera] = PATHS_AUTO_EXPORT[camera]

    date_str, paths_today = check_date(auto_export_paths=auto_export_paths)

    times = dict(state_change=None, shot_change=None, shot_expected=None)
    n_files = {camera: 0 for camera, active in active_cameras.items() if active}
    recording = False
    ops_hours = True
    shot_recorded_last = None
    loop_cnt = 0

    while True:
        loop_cnt += 1
        t_now = datetime.datetime.now()
        shot, state, times, shot_updated, state_updafted = update_state_and_shot(FPATH_MSG_LOG, shot, state, times)

        if ((t_now.time() > START_TIME) and (t_now.time() < STOP_TIME)) or state_updafted:
            time.sleep(TIME_REFRESH_MAIN_LOOP_OPS)

            if not ops_hours:
                logger.info('>>> GOOD MORNING <<<')
                ops_hours = True
                if AUTOMATE_DAPROXY:
                    daproxy.kill_da_proxy(proc_da_proxy)

            if loop_cnt % LOOP_COUNT_UPDATE == 0:
                date_str, paths_today = check_date(auto_export_paths=auto_export_paths)
                pass
        else:
            if ops_hours:
                ops_hours = False
                logger.info(f'>>> GOODNIGHT (Resuming at {START_TIME}) <<<')
            time.sleep(TIME_REFRESH_MAIN_LOOP_NON_OPS)
            continue

            # update_remote_log(logger=logger)

        if (shot_updated) and (shot_recorded_last != shot-1):
            logger.warning(f'A shot has been missed! Last recorded shot was {shot_recorded_last}')

        dt_shot = (times['shot_expected'] - t_now).total_seconds() if (times['shot_expected'] is not None) else None
        if dt_shot is None:
            continue

        dt_recording_finished = (times['finish_recording'] - t_now).total_seconds()
        dt_re_arm = (times['re-arm'] - t_now).total_seconds()

        # print(f'times: {times}')
        # print(f't_now: {t_now}')
        # logger.info(f't_shot_expected: {times.get("shot_expected")}')


        if (dt_shot >= 0):
            logger.info(f'Shot expected in dt: {dt_shot:0.1f} s')

            if (dt_shot <= TIME_RECORD_PRE_SHOT) and (not recording):
                # Start recording protection views
                if active_cameras['Px_protection']:
                    start_recording_research_ir(PIXEL_COORDS_IMAGE['Px_protection'], 'Px_protection')
                if active_cameras['SW_beam_dump']:
                    start_recording_research_ir(PIXEL_COORDS_IMAGE['SW_beam_dump'], 'SW_beam_dump')
                recording = True

            else:
                if active_cameras['MWIR1']:
                    # Make sure MWIR1 is armed (should already be after last shot)
                    start_recording_research_ir(PIXEL_COORDS_IMAGE['MWIR1'], camera='MWIR1')
                if active_cameras['LWIR1']:
                    raise NotImplementedError
    
            if (dt_recording_finished >= 0):
                logger.info(f'Recording should finish in dt: {dt_recording_finished} s')


        if (dt_recording_finished <= 0) and (recording):
            # Protection recordings complete, rename files and organise into todays date folders
            recording = False
            shot_recorded_last = shot
            for camera, active in active_cameras.items():
                if active:
                    n_files[camera] = organise_new_movie_file(PATHS_AUTO_EXPORT[camera], FNS_FORMAT_MOVIE[camera], shot,
                                                    path_export_today=paths_today[camera], n_file_prev=n_files[camera],
                                                    t_shot_change=times['shot_change'])

        if (dt_re_arm <= 0):
            if active_cameras['MWIR1']:
                logger.info('Re-arming MWIR1')
                start_recording_research_ir(PIXEL_COORDS_IMAGE['MWIR1'], camera='MWIR1')
            if active_cameras['LWIR1']:
                logger.info('Re-arming LWIR1')
                raise NotImplementedError


if __name__ == '__main__':
    automate_ax5_camera_researchir()
    pass