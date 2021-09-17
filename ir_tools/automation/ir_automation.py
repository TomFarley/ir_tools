#!/usr/bin/env python

"""


Created: 
"""
import csv
import logging
import os
import shutil
import time
from datetime import datetime
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)
logger.propagate = False


def auto_update_next_shot_file(fn_shot='~/ccfepc/T/tfarley/next_mast_u_shot_no.csv',
                               t_refresh=2.0, t_delay=3.0, n_print=8,
                               organise_ircam_raw=False, organise_flir_ats=False,
                                rit_intershot_job=False, rir_intershot_job=False,
                               run_sched=False):
    fn_shot = Path(fn_shot).expanduser().resolve()
    print(f'Shot no csv file path: {fn_shot}')
    n = 0
    while True:
        try:
            shot_no_last = latest_uda_shot_number()
            shot_no_next = shot_no_last + 1
            update_next_shot_file(shot_no_next, fn_shot=fn_shot, t_delay=t_delay * (n > 0), verbose=(n % n_print == 0),
                                  organise_ircam_raw=organise_ircam_raw, organise_flir_ats=organise_flir_ats, rit_intershot_job=rit_intershot_job,
                                  rir_intershot_job=rir_intershot_job,
                                  run_sched=run_sched)
            time.sleep(t_refresh * 60)
            n += 1
        except KeyboardInterrupt:
            print(f'{datetime.now()}: Script terminated')
            break
        pass

def update_next_shot_file(shot_no_next, fn_shot='~/ccfepc/T/tfarley/next_mast_u_shot_no.csv',
                          t_delay=0, organise_ircam_raw=False, organise_flir_ats=False,
                          rit_intershot_job=False, rir_intershot_job=False,
                          run_sched=False, verbose=True):
    shot_no_file = read_shot_number(fn_shot=fn_shot)

    if (shot_no_file != shot_no_next) or (shot_no_file is None):
        if shot_no_file is None:
            t_delay = 0
        print(f'{datetime.now()}: Incorrect shot number "{shot_no_file}" in {fn_shot} (should be "{shot_no_next}", '
              f'diff={shot_no_next-shot_no_file if shot_no_file is not None else "N/A"}). '
              f'Waiting {t_delay} mins to update file')
        time.sleep(t_delay*60)
        write_shot_number(fn_shot=fn_shot, shot_number=shot_no_next)

        if organise_ircam_raw:
            from fire.scripts.organise_ircam_raw_files import organise_ircam_raw_files
            print(f'{datetime.now()}: Organising IRcam raw files')
            camera_settings = dict(camera='rit', fps=400, exposure=0.25e-3, lens=25e-3, t_before_pulse=1e-1)
            path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/{today}/'
            try:
                organise_ircam_raw_files(path_in=path_in, camera_settings=camera_settings, n_files=1, write_ipx=True)
            except OSError as e:
                logger.warning(f'Failed to organise IRam raw files: {e}')

        if organise_flir_ats:
            from fire.scripts.organise_ircam_raw_files import convert_ats_files_archive_to_ipx
            path_in = '~/data/movies/mast_u/rir_ats_files/{date}'
            fn_meta = '/home/tfarley/data/movies/mast_u/rir_ats_files/rir_meta.json'
            convert_ats_files_archive_to_ipx(pulses=[shot_no_file], path_in=path_in, copy_ats_file=True, fn_meta=fn_meta)

        if rit_intershot_job:
            from ir_tools.automation.rit_analyse_last_shot import submit_rit_intershot_job
            submit_rit_intershot_job()

        if rir_intershot_job:
            from ir_tools.automation.rir_analyse_last_shot import submit_rir_intershot_job
            submit_rir_intershot_job()

        if run_sched:
            # TODO: Run analysis in batch job
            print(f'{datetime.now()}: Running scheduler workflow')
            try:
                from fire.scripts.scheduler_workflow import scheduler_workflow
                scheduler_workflow(shot_no_next-1, camera='rit', machine='MAST_U')
            except Exception as e:
                print(e)
                logger.warning(e)
    else:
        if verbose:
            print(f'{datetime.now()}: Shot number {shot_no_file} is correct')

def latest_uda_shot_number():
    import pyuda
    client = pyuda.Client()
    shot_no_last = int(client.latest_shot())
    return shot_no_last

def monitor_uda_latest_shot(t_refresh=2):
    shot_no_prev = None
    while True:
        try:
            shot_no_current = latest_uda_shot_number()
            print(f'{shot_no_current} ({datetime.now()})')
            if shot_no_current != shot_no_prev:
                print(f'\n********** Shot no updated at {datetime.now()} **********\n')
            shot_no_prev = shot_no_current
            time.sleep(t_refresh)
        except KeyboardInterrupt:
            print(f'{datetime.now()}: Script terminated')
            break
        pass


def click(x, y):
    import win32api, win32con
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def move_mouse(x, y):
    import win32api, win32con
    """Move mouse. x, y units are not display pixel coords"""
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE, x, y, 0, 0)


def get_fns_and_dirs(path_hdd_out):
    fns = []
    for i, (dirpath, dirnames, filenames) in enumerate(os.walk(path_hdd_out)):
        fns.append(filenames)
        if i == 0:
            dirs_top = dirnames
            n_dirs = len(dirnames)
    fns = list(np.concatenate(fns))
    # print(f'Current numnber of dirs: {n_dirs}')
    return fns, dirs_top

def filenames_in_dir(path):
    f = []
    for (dirpath,dirnames,filenames) in os.walk(path):
        f.append(filenames)
        break
    f = list(np.concatenate(f))
    return f

def mkdir(path, parents=True):
    path = Path(path)
    if (not path.is_dir()):
        path.mkdir(exist_ok=True, parents=parents)
        print(f'Created new directory {path}')

def copy_files(path_from, path_to, append_from_name=False, create_destination=True):
    if append_from_name:
        path_to = path_to / path_from.name
    if create_destination:
        mkdir(path_to)
    fns, dirs = get_fns_and_dirs(path_from)
    for fn in fns:
        fn_from = Path(path_from) / fn
        fn_to = Path(path_to) / fn
        try:
            fn_to.write_bytes(fn_from.read_bytes())
        except FileNotFoundError as e:
            print(f'\nFailed to copy file from {path_from} to {path_to}:\n{e}\n')

    print(f'Coppied {fns} from {path_from} to {path_to}')
    time.sleep(1)


def copy_dir(path_from, path_to, append_from_name=True):
    if append_from_name:
        path_to = path_to / path_from.name
    if not path_to.is_dir():
        path_to.mkdir()
        print(f'Created new directory {path_to}')
    try:
        shutil.copytree(path_from, path_to, dirs_exist_ok=True)
    except Exception as e:
        print(e)
    else:
        print(f'Copied {path_from} to {path_to}')
    time.sleep(0.5)


def delete_files_in_dir(path, glob='*'):
    deleted_files = []
    for file in path.glob(glob):
        if file.is_file():
            deleted_files.append(str(file.name))
            file.unlink()
    print(f'Deleted files {deleted_files} in {path}')


def read_shot_number(fn_shot):
    fn_shot = Path(fn_shot).expanduser()
    try:
        with open(fn_shot) as csv_file:
            reader = csv.reader(csv_file)
            data = []
            for row in reader:
                data.append(row)
        shot_number = int(data[0][0])
        # print(f'Read shot number {shot_number} from {fn_shot} ({datetime.now()}')
    except Exception as e:
        shot_number = None
        print(f'{datetime.now()}: Failed to read shot number file: {fn_shot}')
    return shot_number


def write_shot_number(fn_shot, shot_number):
    fn_shot = Path(fn_shot).expanduser().resolve()
    try:
        with open(fn_shot, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([shot_number])
    except Exception as e:
        print(e)
    else:
        print(f'{datetime.now()}: Wrote shot number {shot_number} to {fn_shot}')

if __name__ == '__main__':
    fn = '~/data/movies/diagnostic_pc_transfer/next_mast_u_shot_no.csv'
    # fn = '~/ccfepc/T/tfarley/next_mast_u_shot_no.csv'
    auto_update_next_shot_file(fn_shot=fn, t_refresh=0.25, t_delay=2.5, n_print=40, organise_ircam_raw=False,
                               rit_intershot_job=True, rir_intershot_job=True)
    # monitor_uda_latest_shot()
    # update_next_shot_file(44140)
