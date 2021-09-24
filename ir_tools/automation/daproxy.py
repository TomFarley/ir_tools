#!/usr/bin/env python

"""
Using daproxy technique from MWI:
https://git.ccfe.ac.uk/multi_wavelength_imaging/hardware_interface_code/-/blob/main/run.py

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

logger = logging.getLogger(__name__)
logger.propagate = False


PATH_MSG_LOG = r'D:/mastda/DAProxy/log/'
FNAME_MSG_LOG = f'prx{datetime.datetime.now().strftime("%y%m%d")}'
FPATH_MSG_LOG = Path(PATH_MSG_LOG) / FNAME_MSG_LOG
FPATH_DA_PROXY = r'D:/mastda/DAProxy/proxy.exe'

YES = '✓'
NO = '✕'



def run_da_proxy(fpath_da_proxy):
    # run 'da_proxy' process to connect to MAST-U central messaging server
    logger.info('Starting da_proxy')
    proc_da_proxy = subprocess.Popen(fpath_da_proxy)  # , shell=True, )
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


def get_state(logger=None):
    """ get current MAST-U state from MSG_LOG """
    states = {  # from N. Thomas-Davies
        '1': 'Stop',
        '2': 'Exit',
        '3': 'Idle',
        '4': 'Run',
        '5': 'Ready',
        '6': 'PreShot',  # PreShot comes ~2min before shot
        '8': 'Trigger',
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
    state = states[from_msg_log('state', logger=logger)]

    if logger is not None:
        logger.info('state: ' + state)

    return state


def get_shot(logger=None):
    """ get current shot number from MSG_LOG """
    shot = from_msg_log('shot', logger=logger)

    if logger is not None:
        logger.info('shot: ' + shot)

    return shot


def from_msg_log(field, logger=None):
    """ get current value corresponding to given field (str) from MSG LOG """
    try:
        tail = subprocess.run(['tail', '-n', '1', FPATH_MSG_LOG], stdout=subprocess.PIPE, ).stdout.decode()
        val = tail[tail.find(field + '='):][len(field + '='):]
        val = val[:val.find('&')]

    except Exception as e:
        val = 'UNDEFINED'
        if logger is not None:
            logger.info('from_msg_log: ' + repr(e))

    return val


if __name__ == '__main__':
    pass