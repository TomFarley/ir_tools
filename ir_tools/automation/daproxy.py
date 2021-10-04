#!/usr/bin/env python

"""
Using daproxy technique from MWI:
https://git.ccfe.ac.uk/multi_wavelength_imaging/hardware_interface_code/-/blob/main/run.py

To set up daproxy, just copy mastda directory and set upx address and server name in config file

Created: 
"""

import logging, os, datetime
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path
import subprocess, time, signal

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from ir_tools.automation import automation_tools

logger = logging.getLogger(__name__)
logger.propagate = False


PATH_MSG_LOG = r'D:/mastda/DAProxy/log/'
FNAME_MSG_LOG = f'prx{datetime.datetime.now().strftime("%y%m%d")}.log'
FPATH_MSG_LOG = Path(PATH_MSG_LOG) / FNAME_MSG_LOG
FPATH_DA_PROXY = r'D:/mastda/DAProxy/proxy.exe'

YES = '✓'
NO = '✕'



def run_da_proxy(fpath_da_proxy, windows=True):
    # run 'da_proxy' process to connect to MAST-U central messaging server
    logger.info('Starting da_proxy')
    if windows:
        proc_da_proxy = subprocess.call(fpath_da_proxy)
    else:
        proc_da_proxy = subprocess.Popen(fpath_da_proxy, shell=True, )

    time.sleep(5)  # da_proxy takes a couple of seconds to output its log file
    return proc_da_proxy

def kill_da_proxy(proc_da_proxy):
    try:
        os.kill(proc_da_proxy.pid, signal.SIGINT)
        time.sleep(2)
        assert proc_da_proxy.poll() is not None
        logger.info('kill_da_proxy: ' + YES)
    except Exception as e:
        logger.info('kill_da_proxy: ' + NO)
        logger.info('kill_da_proxy: ' + repr(e))

def daproxy_control():
    REFRESH_TIME_MAIN_LOOP = 5  # sec. The MAST-U Abort state seems to only last for ~10s
    UPDATE_REMOTE_LOG_EVERY = 50  # loops. No point in updating this too often as Github pages site lag by ~20 min
    STOP_TIME = datetime.time(20, 10)
    SEND_DATA_TO_SCRATCH_CAM_NOS = [6, 7, 9, ]

    # ----------------------------------------------------------------------------------------------------------------------
    # PREAMBLE
    # ----------------------------------------------------------------------------------------------------------------------


    state = None
    shot = None
    proc_hic = None
    hic_log = None
    mtime_msg_log_0 = 0
    mtime_config_0 = 0
    shot_0 = 0
    hic_running = False
    loop_cnt = 0
    logger.info('Starting acquisition loop')





    signal.signal(signal.SIGINT, sigint_handler)

    # ----------------------------------------------------------------------------------------------------------------------
    # MAIN MWI ACQUISITION LOOP
    # ----------------------------------------------------------------------------------------------------------------------
    while True:
        # if MSG_LOG changed, update MAST-U shot + state
        mtime_msg_log = os.stat(FPATH_MSG_LOG).st_mtime
        if mtime_msg_log != mtime_msg_log_0:
            mtime_msg_log_0 = mtime_msg_log
            shot, state = get_shot(logger=logger), get_state(logger=logger)
            msg_log_changed = True

        # if (top-level) config changed, update .ini files
        mtime_config = os.stat(FPATH_CONFIG_TOP).st_mtime
        if mtime_config != mtime_config_0:
            mtime_config_0 = mtime_config
            write_config_ini(shot, logger=logger)

        if shot != shot_0:
            shot_0 = shot
            write_config_ini(shot, logger=logger)
            # kill hic if shot changes while hic_running: we either missed the trigger or it was a trigger-less test shot
            if hic_running:
                kill_hic()
                logger.info('HIC killed: shot number changed')

        if hic_running is not True and state == 'PreShot':  # PreShot comes ~2min before shot
            arp_out = arm_red_pitaya(logger=logger)
            # TODO REMOTE RED PITAYA REBOOT IF ARP_OUT != 0

            with open(FPATH_HIC_LOG, 'a') as hic_log:
                proc_hic = subprocess.Popen(
                    './run-rfm-mthreaded',
                    stdout=hic_log,
                    stderr=hic_log,
                    shell=True,
                )
            hic_running = True
            logger.info('HIC running')

        # catch end of HIC
        if hic_running:
            out = proc_hic.poll()
            if out is not None:
                hic_finished()
                if proc_hic.poll() != 0:
                    logger.info('HIC: ' + NO)
                    break  # necessary to break main loop when ctrl + c called in terminal
                logger.info('HIC: ' + YES)
                mdsplus_to_hdf5(shot, logger=logger)
                if freia_access:
                    send_preview_to_scratch(shot, logger=logger)
                    send_data_to_scratch(shot, cam_nos=SEND_DATA_TO_SCRATCH_CAM_NOS, logger=logger)
                update_remote_log(logger=logger)
                shot = get_shot()

        if hic_running and state == 'Abort':
            kill_hic()
            logger.info('HIC killed: MAST-U Abort state')

        if datetime.datetime.now().time() > STOP_TIME:
            kill_hic()
            kill_da_proxy()
            logger.info('>>> GOODNIGHT <<<')
            update_remote_log(logger=logger)
            break

        if loop_cnt % UPDATE_REMOTE_LOG_EVERY == 0:
            update_remote_log(logger=logger)

        loop_cnt += 1
        time.sleep(REFRESH_TIME_MAIN_LOOP)

def update_estimated_shot_time(state, time_entered_state, shot_time_estimate_prev=None):
    """Improve estimated time shot will run based on typical times states are entered"""
    delays = {
        'Ready': 110,  # ~1min 50s before shot
        'PreShot': 105,  # PreShot comes ~1min 45s before shot
        'Trigger': 15,  # ~15 s before shot
        'Abort': -30,  # Effectively after shot
    }
    delay = delays.get(state, None)
    if delay is not None:
        shot_time_estimate = time_entered_state + datetime.timedelta(seconds=delay)
    else:
        shot_time_estimate = shot_time_estimate_prev
    return shot_time_estimate, delay        

def get_state(fn , logger=None):
    """ get current MAST-U state from MSG_LOG """
    states = {  # from N. Thomas-Davies
        '1': 'Stop',
        '2': 'Exit',
        '3': 'Idle',
        '4': 'Run',
        '5': 'Ready',  # ~1min 50s before shot
        '6': 'PreShot',  # PreShot comes ~1min 45s before shot
        '8': 'Trigger',  # ~15 s before shot
        '9': 'PostShot',
        '10': 'Reset',
        '11': 'Abort',
        '12': 'DataFile',
        '14': 'Init',
        '19': 'WaitArm',
        '20': 'WaitEnd',
        '29': 'Fault',
        '30': 'Connect',
        '34': 'Set',
        '35': 'Arm',
        'UNDEFINED': 'UNDEFINED',
    }
    state_no = from_msg_log(fn, 'state', logger=logger)
    if state_no in states:
        state = states[state_no]
    else:
        print(f'Machine state not recognised: "{state_no}"')
        state = 'UNDEFINED'

    if logger is not None:
        logger.info('state: ' + state)

    return state


def get_shot(fn, logger=None):
    """ get current shot number from MSG_LOG """
    shot = from_msg_log(fn, 'shot', logger=logger)

    if logger is not None:
        logger.info('shot: ' + shot)

    if shot in ('', 'UNDEFINED'):
        print(f'Failed to retrieve shot number')
    else:
        try:
            shot = int(shot)
        except Exception as e:
            print(f'Bad value for shot from daproxy: {e}. Set shot to 0.')
            shot = 0

    return shot

def get_last_line_windows(fn):
    with open(fn, 'r') as f:
        lines = f.read().splitlines()
        last_line = lines[-1]
    return last_line

def get_last_line_unix():
    tail = subprocess.run(['tail', '-n', '1', fn], stdout=subprocess.PIPE, ).stdout.decode()
    return tail


def from_msg_log(fn, field, logger=None):
    """ get current value corresponding to given field (str) from MSG LOG """
    if not Path(fn).is_file():
        logger.warmomg(f'Log file not found: {fn}')
    try:
        tail = get_last_line_windows(fn)
        val = tail[tail.find(field + '='):][len(field + '='):]
        val = val[:val.find('&')]

    except Exception as e:
        val = 'UNDEFINED'
        if logger is not None:
            logger.info('from_msg_log: ' + repr(e))

    return val


if __name__ == '__main__':
    pass


def update_state_and_shot(FPATH_MSG_LOG, shot_prev, state_prev, times):
    from ir_tools.automation.run_ir_automation import TIME_DURATION_RECORD, TIME_RECORD_PRE_SHOT, TIME_DELAY_REARM
    modified_da_log, t_state_change = automation_tools.file_updated(FPATH_MSG_LOG, t_mod_prev=times['state_change'])
    if modified_da_log:
        shot, state = get_shot(fn=FPATH_MSG_LOG), get_state(fn=FPATH_MSG_LOG)
        times['state_change'] = t_state_change
        times[state] = t_state_change

        if shot != shot_prev:
            logger.info(f'{BARS} Shot number changed to {shot}. State: "{state}" {BARS}')
        else:
            # if state in ('Ready', 'PreShot', 'Trigger', 'Abort'):
            # if state_prev is not None:
            logger.info(f'In state "{state}" for shot {shot}')

        shot_time_estimate, delay = update_estimated_shot_time(state, t_state_change, times.get('shot_expected'))
        times['shot_expected'] = shot_time_estimate

        if shot_time_estimate is not None:
            times['finish_recording'] = times['shot_expected'] + datetime.timedelta(seconds=TIME_DURATION_RECORD-TIME_RECORD_PRE_SHOT)
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
