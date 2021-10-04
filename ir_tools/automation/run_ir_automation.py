#!/usr/bin/env python

"""Script to automate collection of IR camera data using manufacturer GUI applications and DAproxy to get machine state
info. Replaces previous scripts without DAproxy.
Works with FLIR ResearchIR software for SC7500 cameras and AX5 protection cameras
Works with IRCAM Works for Velox cameras

Created: Tom Farley
Date: Sept 2021
"""

import logging, signal, time, datetime, os
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

from ir_tools.automation import automation_tools, daproxy, flir_researchir_automation, ircam_works_automation
from ir_tools.automation.daproxy import FPATH_DA_PROXY, FPATH_MSG_LOG, get_shot, get_state
from ir_tools.automation.automation_tools import make_iterable

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

AUTOMATE_DAPROXY = True

FPATH_LOG = Path('MWIR1_pc.log')

TIME_REFRESH_MAIN_LOOP_OPS = 25  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_REFRESH_MAIN_LOOP_PRESHOT = 1  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_REFRESH_MAIN_LOOP_NON_OPS = 10*60  # sec. The MAST-U Abort state seems to only last for ~10s
TIME_DELEY_PRESHOT = 105  # sec. PreShot comes ~2min before shot
TIME_RECORD_PRE_SHOT = 6  # sec. How long before shot is expected to start recording
TIME_DURATION_RECORD = 25  # sec. Duration of movie recording set in ResearchIR
TIME_DELAY_REARM = 120  # sec. Time to wait for clock train to finish.
TIME_TYPICAL_MIN_INTERSHOT = 3 * 60  # sec. Normally at least 3 min between shots

LOOP_COUNT_UPDATE = 8  # loops. No point in updating this too often as Github pages site lag by ~20 min
STOP_TIME = datetime.time(20, 10)
START_TIME = datetime.time(7, 50)

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

def automate_ir_cameras(active_cameras=()):
    active_cameras = dict(active_cameras)
    if len(active_cameras) == 0:
        raise ValueError('No active cameras')

    logger.info(
        f'Starting camera automation for cameras: '
        f'{", ".join([camera for camera, active in active_cameras.items() if active])}')

    if AUTOMATE_DAPROXY:
        proc_da_proxy = daproxy.run_da_proxy(FPATH_DA_PROXY)
    else:
        proc_da_proxy = None

    signal.signal(signal.SIGINT, automation_tools.sigint_handler(proc_da_proxy))

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

    date_str, paths_today = automation_tools.check_date(auto_export_paths=auto_export_paths)

    armed = automation_tools.arm_scientific_cameras(active_cameras, armed={})

    times = dict(state_change=None, shot_change=None, shot_expected=None)

    n_files = {camera: 0 for camera, active in active_cameras.items() if active}
    recording = False
    ops_hours = True
    shot_recorded_last = None
    loop_cnt = 0

    while True:
        loop_cnt += 1
        t_now = datetime.datetime.now()
        shot, state, times, shot_updated, state_updafted = daproxy.update_state_and_shot(FPATH_MSG_LOG, shot, state, times)

        if ((t_now.time() > START_TIME) and (t_now.time() < STOP_TIME)) and (t_now.weekday() <= 5) or state_updafted:
            if state in ('PreShot', 'Trigger'):
                time.sleep(TIME_REFRESH_MAIN_LOOP_PRESHOT)
            else:
                time.sleep(TIME_REFRESH_MAIN_LOOP_OPS)

            if not ops_hours:
                logger.info('>>> GOOD MORNING <<<')
                logger.info(f'{BARS} Waiting for shot {shot+1}. State: "{state}" {BARS}')
                ops_hours = True
                if AUTOMATE_DAPROXY:
                    daproxy.kill_da_proxy(proc_da_proxy)

            if loop_cnt % LOOP_COUNT_UPDATE == 0:
                date_str, paths_today = automation_tools.check_date(auto_export_paths=auto_export_paths)
                pass
        else:
            if ops_hours:
                ops_hours = False
                logger.info(f'>>> GOODNIGHT (Resuming at {START_TIME}) <<<')
            time.sleep(TIME_REFRESH_MAIN_LOOP_NON_OPS)
            continue

            # update_remote_log(logger=logger)

        if (shot_updated) and (shot_recorded_last != shot - 1):
            logger.warning(f'A shot has been missed! Last recorded shot was {shot_recorded_last}')

        t_now = datetime.datetime.now()
        dt_shot = (times['shot_expected'] - t_now).total_seconds() if (times['shot_expected'] is not None) else None
        if dt_shot is None:
            continue

        dt_recording_finished = (times['finish_recording'] - t_now).total_seconds()
        dt_re_arm = (times['re-arm'] - t_now).total_seconds()

        # print(f'times: {times}')
        # print(f't_now: {t_now}')
        # logger.info(f't_shot_expected: {times.get("shot_expected")}')

        if (dt_shot >= 0):
            if (loop_cnt % LOOP_COUNT_UPDATE == 0) or (dt_shot < 7):
                logger.info(f'Shot expected in dt: {dt_shot:0.1f} s')

            if (dt_shot <= TIME_RECORD_PRE_SHOT) and (not recording):
                logger.info(
                    f'Starting protection cameras recording {TIME_RECORD_PRE_SHOT:0.1f}s before shot for {TIME_DURATION_RECORD:0.1f}s')
                # Start recording protection views
                if active_cameras['Px_protection']:
                    flir_researchir_automation.start_recording_research_ir(PIXEL_COORDS_IMAGE['Px_protection'], 'Px_protection')
                if active_cameras['SW_beam_dump']:
                    flir_researchir_automation.start_recording_research_ir(PIXEL_COORDS_IMAGE['SW_beam_dump'], 'SW_beam_dump')
                recording = True

            else:
                # TIME_RECORD_PRE_SHOT before shot
                armed = automation_tools.arm_scientific_cameras(active_cameras, armed)


        elif (dt_recording_finished >= 0):
            if (loop_cnt % LOOP_COUNT_UPDATE == 0) or (dt_recording_finished < 2):
                logger.info(f'Recording should finish in dt: {dt_recording_finished:0.1f} s')

        if (dt_recording_finished <= -5) and (recording):
            # Protection recordings complete, rename files and organise into todays date folders
            recording = False
            shot_recorded_last = shot

            for camera in ('LWIR1', 'LWIR2', 'MWIR3'):
                if active.get(camera, False):
                    ircam_works_automation.export_movie(shot_number=shot, camera=camera, check_unarmed=True)

            for camera, active in active_cameras.items():
                if active:
                    n_files[camera] = automation_tools.organise_new_movie_file(PATHS_AUTO_EXPORT[camera], FNS_FORMAT_MOVIE[camera], shot,
                                                              path_export_today=paths_today[camera],
                                                              n_file_prev=n_files[camera],
                                                              t_shot_change=times['shot_change'])
                    armed[camera] = False

        if (dt_re_arm <= 0) or (state == 'PostShot'):
            armed = automation_tools.arm_scientific_cameras(active_cameras, armed)


if __name__ == '__main__':
    host = os.environ['COMPUTERNAME']
    # TODO: Set with argpass?
    if host == 'MWIR-PC1':
        active_cameras = {'LWIR1': False, 'MWIR1': True, 'Px_protection': True, 'SW_beam_dump': False}
        # active_cameras = {'LWIR1': False, 'MWIR1': False, 'Px_protection': True, 'SW_beam_dump': False}
    else:
        active_cameras = {'LWIR1': True, 'MWIR1': False, 'Px_protection': False, 'SW_beam_dump': False}
    logger.info(f'Starting automation on "{host}" PC ')

    automate_ir_cameras(active_cameras=active_cameras)
    pass