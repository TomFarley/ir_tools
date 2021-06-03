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
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

import pyuda

logger = logging.getLogger(__name__)
logger.propagate = False

client = pyuda.Client()


def auto_update_next_shot_file(fn_shot='/home/tfarley/ccfepc/T/tfarley/next_mast_u_shot_no.csv', t_refresh=1,
                               n_print=5):
    n = 0
    while True:
        try:
            shot_no_file = read_shot_number(fn_shot=fn_shot)
            shot_no_last = int(client.latest_shot())
            shot_no_next = shot_no_last + 1
            if shot_no_file != shot_no_next:
                print(f'Incorrect shot number {shot_no_file} in {fn_shot}: {datetime.now()}')
                write_shot_number(fn_shot=fn_shot, shot_number=shot_no_next)
            else:
                if n // n_print == 0:
                    print(f'Shot number {shot_no_file} is correct: {datetime.now()}')
            time.sleep(t_refresh * 60)
            n += 1
        except KeyboardInterrupt:
            print(f'Script terminated: {datetime.now()}')
            break
        pass


def click(x, y):
    import win32api, win32con
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def move(x, y):
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


def copy_files(path_from, path_to, append_from_name=False):
    if append_from_name:
        path_to = path_to / path_from.name
    if not path_to.is_dir():
        path_to.mkdir()
        print(f'Created new directory {path_to}')
    fns, dirs = get_fns_and_dirs(path_from)
    for fn in fns:
        fn_from = Path(path_from) / fn
        fn_to = Path(path_to) / fn
        fn_to.write_bytes(fn_from.read_bytes())
    print(f'Coppied {fns} from {path_from} to {path_to}')
    time.sleep(1)


def copy_dir(path_from, path_to, append_from_name=True):
    if append_from_name:
        path_to = path_to / path_from.name
    if not path_to.is_dir():
        path_to.mkdir()
        print(f'Created new directory {path_to}')
    shutil.copytree(path_from, path_to, dirs_exist_ok=True)
    print(f'Copied {path_from} to {path_to}')
    time.sleep(1)


def delete_files_in_dir(path, glob='*'):
    deleted_files = []
    for file in path.glob(glob):
        if file.is_file():
            deleted_files.append(str(file.name))
            file.unlink()
    print(f'Deleted files {deleted_files} in {path}')


def read_shot_number(fn_shot):
    with open(fn_shot) as csv_file:
        reader = csv.reader(csv_file)
        data = []
        for row in reader:
            data.append(row)
    shot_number = int(data[0][0])
    # print(f'Read shot number {shot_number} from {fn_shot}')
    return shot_number


def write_shot_number(fn_shot, shot_number):
    with open(fn_shot, 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([shot_number])
    print(f'Wrote shot number {shot_number} to {fn_shot}')


if __name__ == '__main__':
    auto_update_next_shot_file()
