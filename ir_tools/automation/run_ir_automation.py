#!/usr/bin/env python

"""Script to automate collection of IR camera data using manufacturer GUI applications and DAproxy to get machine state
info. Replaces previous scripts without DAproxy.
Works with FLIR ResearchIR software for SC7500 cameras and AX5 protection cameras
Works with IRCAM Works for Velox cameras

Created: Tom Farley
Date: Sept 2021
"""

import logging, signal, time, datetime, os

import numpy as np

from ir_tools.automation import automation_tools, daproxy, flir_researchir_automation, ircam_works_automation
from ir_tools.automation.automation_settings import (PATHS_AUTO_EXPORT, PATHS_FREIA_EXPORT, FNS_FORMAT_MOVIE,
                                                     AUTOMATE_DAPROXY, TIME_REFRESH_MAIN_LOOP_OPS, TIME_DURATION_RECORD,
                                                     TIME_REFRESH_MAIN_LOOP_PRESHOT, TIME_REFRESH_MAIN_LOOP_NON_OPS,
                                                     TIME_RECORD_PRE_SHOT, LOOP_COUNT_UPDATE, STOP_TIME, START_TIME,
                                                     PIXEL_COORDS_IMAGE, IRCAM_CAMERAS, FLIR_CAMERAS,
                                                     PROTECTION_CAMERAS, FPATH_LOG, BARS)
from ir_tools.automation.daproxy import FPATH_DA_PROXY, FPATH_MSG_LOG, get_shot, get_state

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

    protection_active = np.any([active for camera, active in active_cameras.items() if camera in PROTECTION_CAMERAS])
    ircam_active = np.any([active for camera, active in active_cameras.items() if camera in IRCAM_CAMERAS])
    flir_active = np.any([active for camera, active in active_cameras.items() if camera in FLIR_CAMERAS])

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
        raise FileNotFoundError(f'DAProxy log file doesn\'t not exist: {FPATH_MSG_LOG}')

    shot, state = get_shot(fn=FPATH_MSG_LOG), get_state(fn=FPATH_MSG_LOG)
    logger.info(f'{BARS} Ready for shot {shot+1} in state "{state}" {BARS}')

    auto_export_paths = {}
    for camera, active in active_cameras.items():
        if active:
            auto_export_paths[camera] = PATHS_AUTO_EXPORT[camera]

    date_str, paths_today = automation_tools.check_date(auto_export_paths=PATHS_AUTO_EXPORT,
                            freia_export_paths=PATHS_FREIA_EXPORT, active_cameras=active_cameras, date_prev=None)

    armed = automation_tools.arm_scientific_cameras(active_cameras, armed={}, pixel_coords_image=PIXEL_COORDS_IMAGE)

    logger.info(f'{paths_today}, {armed}, {active_cameras}')

    times = dict(state_change=None, shot_change=None, shot_expected=None)

    n_files = {camera: 0 for camera, active in active_cameras.items() if active}
    recording = False
    ops_hours = True
    shot_recorded_last = None
    loop_cnt = 0

    while True:
        loop_cnt += 1
        t_now = datetime.datetime.now()
        shot, state, times, shot_updated, state_updated = daproxy.update_state_and_shot(FPATH_MSG_LOG, shot, state, times)

        if ((t_now.time() > START_TIME) and (t_now.time() < STOP_TIME)) and (t_now.weekday() <= 5) or state_updated:
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
                date_str, paths_today = automation_tools.check_date(auto_export_paths=PATHS_AUTO_EXPORT,
                                                                    freia_export_paths=PATHS_FREIA_EXPORT,
                                                                    active_cameras=active_cameras, date_prev=date_str)
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
            if (protection_active and (loop_cnt % LOOP_COUNT_UPDATE == 0) or (dt_shot < 7)) or state_updated:
                logger.info(f'Shot {shot} expected in dt: {dt_shot:0.1f} s')

            if (dt_shot <= TIME_RECORD_PRE_SHOT) and (not recording):
                if protection_active:
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
                armed = automation_tools.arm_scientific_cameras(active_cameras, armed, pixel_coords_image=PIXEL_COORDS_IMAGE)


        elif (dt_recording_finished >= 0) and protection_active:
            if (loop_cnt % LOOP_COUNT_UPDATE == 0) or (dt_recording_finished < 2):
                logger.info(f'Recording should finish in dt: {dt_recording_finished:0.1f} s')

        if (dt_recording_finished <= -5) and (recording):
            # Protection recordings complete, rename files and organise into todays date folders
            recording = False
            shot_recorded_last = shot

            for camera in IRCAM_CAMERAS:
                if active_cameras.get(camera, False):
                    ircam_works_automation.export_movie(shot_number=shot, camera=camera, check_unarmed=True)

            for camera, active in active_cameras.items():
                if active:
                    n_files[camera] = automation_tools.organise_new_movie_file(PATHS_AUTO_EXPORT[camera],
                                                                               FNS_FORMAT_MOVIE[camera], shot,
                                                                               path_export_today=paths_today.get(camera),
                                                                               n_file_prev=n_files[camera], t_shot_change=times['shot_change'],
                                                                               camera=camera,
                                                                               path_freia_export=paths_today.get(f'{camera}_freia', None))
                    armed[camera] = False

        if (dt_re_arm <= 0) or (state == 'PostShot'):
            armed = automation_tools.arm_scientific_cameras(active_cameras, armed, pixel_coords_image=PIXEL_COORDS_IMAGE)


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