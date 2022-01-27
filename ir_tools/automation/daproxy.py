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

PATH_MSG_LOG = r'D:/mastda/DAProxy/log/'
FNAME_MSG_LOG = f'prx{datetime.datetime.now().strftime("%y%m%d")}.log'
FPATH_MSG_LOG = Path(PATH_MSG_LOG) / FNAME_MSG_LOG
FPATH_DA_PROXY = r'D:/mastda/DAProxy/proxy.exe'

YES = '✓'
NO = '✕'
BARS = '='*10

def run_da_proxy(fpath_da_proxy, windows=True):
    # run 'da_proxy' process to connect to MAST-U central messaging server
    logger.info('Attempting to start da_proxy')
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

def update_estimated_shot_time(state, time_entered_state, shot_time_estimate_prev=None):
    """Improve estimated time shot will run based on typical times states are entered"""
    delays = {
        'Ready': 110,  # ~1min 50s before shot
        'PreShot': 105,  # PreShot comes ~1min 45s before shot
        'Trigger': 15,  # ~15 s before shot
        'Abort': -60,  # Effectively after shot
        # 'UNDEFINED': np.nan
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

def update_state_and_shot(FPATH_MSG_LOG, shot_prev, state_prev, times):
    from ir_tools.automation.automation_settings import TIME_DELAY_REARM
    from ir_tools.automation.automation_settings import TIME_DURATION_RECORD
    from ir_tools.automation.automation_settings import TIME_RECORD_PRE_SHOT
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


if __name__ == '__main__':
    pass
