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
                               t_refresh=2, t_delay=3, n_print=8):
    fn_shot = Path(fn_shot).expanduser().resolve()
    n = 0
    while True:
        try:
            shot_no_last = latest_uda_shot_number()
            shot_no_next = shot_no_last + 1
            update_next_shot_file(shot_no_next, fn_shot=fn_shot, t_delay=t_delay * (n > 0), verbose=(n % n_print == 0))
            time.sleep(t_refresh * 60)
            n += 1
        except KeyboardInterrupt:
            print(f'{datetime.now()}: Script terminated')
            break
        pass

def update_next_shot_file(shot_no_next, fn_shot='~/ccfepc/T/tfarley/next_mast_u_shot_no.csv',
                          t_delay=0, verbose=True):
    shot_no_file = read_shot_number(fn_shot=fn_shot)

    if (shot_no_file != shot_no_next) or (shot_no_file is None):
        if shot_no_file is None:
            t_delay = 0
        print(f'{datetime.now()}: Incorrect shot number "{shot_no_file}" in {fn_shot}. '
              f'Waiting {t_delay} mins to update file')
        time.sleep(t_delay*60)
        write_shot_number(fn_shot=fn_shot, shot_number=shot_no_next)
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
    auto_update_next_shot_file()
    # monitor_uda_latest_shot()
    # update_next_shot_file(44140)
