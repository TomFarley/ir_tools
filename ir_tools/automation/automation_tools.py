#!/usr/bin/env python

"""


Created: 
"""
import csv
import logging
import os, re
import shutil
import time
from datetime import datetime
from typing import Iterable, Optional, Any
from pathlib import Path

import numpy as np
from ir_tools.automation.automation_settings import (IRCAM_CAMERAS, FLIR_CAMERAS, PROTECTION_CAMERAS, FPATH_LOG,
                                                     YES, NO, FREIA_HOME_PATH)

logger = logging.getLogger(__name__)
# fhandler = logging.FileHandler(FPATH_LOG)
# shandler = logging.StreamHandler()
# [i.setLevel('INFO') for i in [logger, fhandler, shandler]]
# formatter = logging.Formatter('%(asctime)s - %(message)s')
# fhandler.setFormatter(formatter)
# shandler.setFormatter(formatter)
# logger.addHandler(fhandler)
# logger.addHandler(shandler)

def make_iterable(obj: Any, ndarray: bool = False,
                  cast_to: Optional[type] = None,
                  cast_dict: Optional = None,
                  # cast_dict: Optional[dict[type,type]]=None,
                  nest_types: Optional = None,
                  ignore_types: Optional = ()) -> Iterable:

    # nest_types: Optional[Sequence[type]]=None) -> Iterable:
    """Return itterable, wrapping scalars and strings when requried.

    If object is a scalar nest it in a list so it can be iterated over.
    If ndarray is True, the object will be returned as an array (note avoids scalar ndarrays).

    Args:
        obj         : Object to ensure is iterable
        ndarray     : Return as a non-scalar np.ndarray
        cast_to     : Output will be cast to this type
        cast_dict   : dict linking input types to the types they should be cast to
        nest_types  : Sequence of types that should still be nested (eg dict)
        ignore_types: Types to not nest (eg if don't want to nest None)

    Returns:

    """
    if not isinstance(ignore_types, (tuple, list)):
        ignore_types = make_iterable(ignore_types, ndarray=False, ignore_types=())
    if (obj in ignore_types) or (type(obj) in ignore_types):
        # Don't nest this type of input
        return obj

    if not hasattr(obj, '__iter__') or isinstance(obj, str):
        obj = [obj]
    if (nest_types is not None) and isinstance(obj, nest_types):
        obj = [obj]
    if (cast_dict is not None) and (type(obj) in cast_dict):
        obj = cast_dict[type(obj)](obj)
    if ndarray:
        obj = np.array(obj)
    if (cast_to is not None):
        if isinstance(cast_to, (type, Callable)):
            if cast_to == np.ndarray:
                obj = np.array(obj)
            else:
                obj = cast_to(obj)  # cast to new type eg list
        else:
            raise TypeError(f'Invalid cast type: {cast_to}')
    return obj

def check_freia_access():

    # check if network drive is mounted
    FPATH_FREIA = 'H:/'
    if os.path.ismount(FPATH_FREIA):
        freia_access = True
        logger.info('freia access: ' + YES)
    else:
        freia_access = False
        logger.info('freia access: ' + NO)

def file_updated(path_fn, t_mod_prev=None):
    t_mod = Path(path_fn).stat().st_mtime
    t_mod = datetime.fromtimestamp(t_mod)

    if (t_mod != t_mod_prev) or (t_mod_prev is None):
        modified = True
    else:
        modified = False
    return modified, t_mod

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
                logger.warning(f'Failed to organise IRcam raw files: {e}')

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


def click_mouse(x_pix, y_pix):
    import win32api, win32con
    win32api.SetCursorPos((x_pix, y_pix))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x_pix, y_pix, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x_pix, y_pix, 0, 0)


def move_mouse(x, y):
    import win32api, win32con
    """Move mouse. x, y units are not display pixel coords"""
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE, x, y, 0, 0)


def get_fns_and_dirs(path):
    """Return all filenames and dirnames recursively from path"""
    if not Path(path).is_dir():
        raise FileNotFoundError(f'Path does not exist: {path}')

    fns = []
    for i, (dirpath, dirnames, filenames) in enumerate(os.walk(path)):
        fns.append(filenames)
        if i == 0:
            dirs_top = dirnames
            n_dirs = len(dirnames)
    fns = list(np.concatenate(fns))
    # print(f'Current numnber of dirs: {n_dirs}')
    return fns, dirs_top

def filenames_in_dir(path):
    path = Path(path).expanduser().resolve()
    f = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        f.append(filenames)
        break
    if len(f) > 0:
        f = list(np.concatenate(f))
    return f

def age_of_file(fn_path, path=None):
    if path is not None:
        fn_path = Path(path) / fn_path
    t_now = datetime.now()
    # t_day = 24*60*60
    t_modified = datetime.fromtimestamp(os.path.getmtime(fn_path))
    dt_age = t_now - t_modified
    return t_modified, dt_age

def sort_files_by_age(fns, path=None):
    fns = make_iterable(fns)

    t_mods = []
    ages_dt = []
    ages_seconds = []
    for fn in fns:
        t_modified, age_dt = age_of_file(fn, path=path)
        t_mods.append(t_modified)
        ages_dt.append(age_dt)
        ages_seconds.append(age_dt.total_seconds())

    i_order = np.argsort(ages_seconds)
    t_mod_sorted = np.array(t_mods)[i_order]
    fns_sorted = np.array(fns)[i_order]
    ages_sorted = np.array(ages_dt)[i_order]
    ages_sec_sorted = np.array(ages_seconds)[i_order]

    return fns_sorted, i_order, t_mod_sorted, ages_sorted, ages_sec_sorted

def shot_nos_from_fns(file_names, pattern='(\d+).ats'):
    saved_pulses = []
    for fn in file_names:
        fn = Path(fn).name
        m = re.match(pattern, fn)
        pulse = int(m.groups()[-1]) if m else None
        saved_pulses.append(pulse)
    return saved_pulses

def mkdir(path, parents=True):
    path = Path(path)
    success = True
    created = False
    if (not path.is_dir()):
        try:
            path.mkdir(exist_ok=True, parents=parents)
        # except FileExistsError as e:
        #     print(f'Failed to create directory "{path}": {e}')
        #     succes = False
        except Exception as e:
            print(f'Failed to create directory "{path}": {e}')
            try:
                os.makedirs(str(path))
            except Exception as e:
                logger.warning(f'Failed to create directory using os.mkdirs: "{path}": {e}')
                success = False
            else:
                created = True
                success = True
        else:
            logger.info(f'Created new directory "{path}"')
            created = True
    return success, created

def copy_files(path_from, path_to, append_from_name=False, create_destination=True):
    if create_destination:
        mkdir(path_to)

    fns, dirs = get_fns_and_dirs(path_from)

    for fn in fns:
        fn_from = Path(path_from) / fn
        fn_to = Path(path_to) / fn
        success = copy_file(fn_from, fn_to, append_from_name=append_from_name, create_destination=False)

    print(f'Copied {fns} from {path_from} to {path_to}')
    # time.sleep(1)

def copy_file(path_fn_from, path_fn_to, append_from_name=False, create_destination=False):
    if append_from_name or path_fn_to.is_dir():
        path_fn_to = path_fn_to / path_fn_from.name

    if create_destination:
        mkdir(path_fn_to.parent)
    else:
        if not path_fn_to.parent.is_dir():
            logger.warning(f'File copy destination directory does not exist: {path_fn_to.parent}')

    success = False
    try:
        path_fn_to.write_bytes(path_fn_from.read_bytes())
    except FileNotFoundError as e:
        logger.warning(f'\nFailed to copy file from {path_fn_from} to {path_fn_to}:\n{e}\n')
    except PermissionError as e:
        logger.warning(f'\nFailed to copy file from {path_fn_from} to {path_fn_to}:\n{e}\n')
    except Exception as e:
        logger.warning(f'\nFailed to copy file from {path_fn_from} to {path_fn_to}:\n{e}\n')
    else:
        success = True
    return success

def copy_dir(path_from, path_to, append_from_name=True):
    if append_from_name:
        path_to = path_to / path_from.name
    if not path_to.is_dir():
        path_to.mkdir()
        print(f'Created new directory {path_to}')
    try:
        shutil.copytree(str(path_from), str(path_to), dirs_exist_ok=True)
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

def move_files_in_dir(path_from, path_to):
    if not path_to.is_dir():
        path_to.mkdir()
        print(f'Created new directory {path_to}')

    fns = filenames_in_dir(path_from)
    fns_moved = []
    for fn in fns:
        path_fn = Path(path_from) / fn
        path_fn_new = Path(path_to) / fn
        success = move_file(path_fn, path_fn_new)
        if success:
            fns_moved.append(fn)
    if len(fns) > 0:
        logger.info(f'Moved {len(fns_moved)} files from "{path_from}" to "{path_to}": {fns_moved}')
        time.sleep(0.5)
    return fns

def move_file(path_fn_old, path_fn_new, verbose=False):
    path_fn_old = Path(path_fn_old)
    try:
        path_fn_old.rename(path_fn_new)
        # path_fn_old.replace(path_fn_new)
    except Exception as e:
        logger.warning(f'Failed to move/rename file from "{path_fn_old}" to "{path_fn_new}')
        success = False
    else:
        success = True
        if verbose:
            logger.info(f'Moved/renamed file from  "{path_fn_old}" to "{path_fn_new}"')
    return success

def read_shot_number(fn_shot):
    fn_shot = Path(fn_shot).expanduser().resolve()
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

def empty_auto_export(path_auto_export):
    path_auto_export_backup = (path_auto_export / '..' / 'auto_export_backup').resolve()
    mkdir(path_auto_export_backup)
    move_files_in_dir(path_auto_export, path_auto_export_backup)
    # ir_automation.copy_files(path_auto_export, path_auto_export_backup)
    # ir_automation.delete_files_in_dir(path_auto_export)  # , glob='*.RAW')
    logger.info(f'Moved previously exported files to {path_auto_export_backup} from {path_auto_export}')


def check_date(auto_export_paths, freia_export_paths, active_cameras, date_str_prev=None, paths_today_prev=None):
    date = datetime.now()
    date_str = date.strftime('%Y-%m-%d')
    if (date.weekday() <= 5) and ((date_str_prev != date_str) or (date_str_prev is None)):
        paths_today = dict()
        # No weekend ops
        for camera, path in auto_export_paths.items():
            if active_cameras.get(camera, False):
                path_export_today = (path / '../dates' / date_str).resolve()
                success, created = mkdir(path_export_today)
                paths_today[camera] = path_export_today
                if created:
                    empty_auto_export(path)
        for camera, path in freia_export_paths.items():
            if active_cameras.get(camera, False):
                path_export_today = (Path(path) / date_str)  # .resolve()
                success, created = mkdir(path_export_today, parents=False)

                if not success:
                    success, created = mkdir(path_export_today.resolve(), parents=False)

                if path_export_today.is_dir():
                    paths_today[f'{camera}_freia'] = path_export_today
    else:
        paths_today = paths_today_prev

    return date_str, paths_today


def sigint_handler(proc_da_proxy):
    from ir_tools.automation import daproxy

    def _sigint_handler(sig, frame):
        logger.info('>>> CTRL+C <<<')
        daproxy.kill_da_proxy(proc_da_proxy)
        raise KeyboardInterrupt
    return _sigint_handler


def arm_scientific_cameras(active_cameras, armed, pixel_coords_image):
    for camera in FLIR_CAMERAS:
        if active_cameras.get(camera, False) and (not armed.get(camera, False)):
            from ir_tools.automation.flir_researchir_automation import start_recording_research_ir
            logger.info(f'Re-arming {camera}')
            start_recording_research_ir(pixel_coords_image[camera], camera=camera)
            armed[camera] = True
    for camera in IRCAM_CAMERAS:
        if active_cameras.get(camera, False) and (not armed.get(camera, False)):
            from ir_tools.automation.ircam_works_automation import start_recording_ircam_works
            logger.info(f'Re-arming {camera}')
            armed[camera] = start_recording_ircam_works(pixel_coords_record=pixel_coords_image[camera],
                                                        armed=armed.get(camera, None), logger=logger)
    return armed


def organise_new_movie_file(path_auto_export, fn_format_movie, shot, path_export_today, n_file_prev, t_shot_change,
                            camera, path_freia_export=None):

    fns_autosaved = filenames_in_dir(path_auto_export)
    fns_sorted, i_order, t_mod, ages, ages_sec = sort_files_by_age(fns_autosaved, path=path_auto_export)
    n_files = len(fns_sorted)
    correct_fn = False

    saved_shots = shot_nos_from_fns(fns_sorted, pattern=fn_format_movie.format(shot='(\d+)'))
    if n_files == n_file_prev:
        logger.warning(f'Number of files, {n_files}, has not changed after shot! {path_auto_export}')

    if n_files > 0:
        fn_new, age_fn_new, age_fn_new_sec, t_mod_fn_new, shot_fn_new = Path(fns_sorted[0]), ages[0], ages_sec[0], t_mod[0], saved_shots[0],
        path_fn_new = path_auto_export / fn_new
        logger.info(f'File "{fn_new}" for shot {shot_fn_new} ({shot} expected) saved {age_fn_new.total_seconds():0.1f} s ago')

        if t_shot_change is not None:
            dt_file_since_shot_change = (t_mod_fn_new - t_shot_change).total_seconds()
        else:
            dt_file_since_shot_change = None

        # TODO: Compare time of shot change to time of file creation
        if (shot_fn_new != shot):

            if (dt_file_since_shot_change is None) or (dt_file_since_shot_change >= 0):
                fn_expected = fn_format_movie.format(shot=f'0{shot}')
                path_fn_expected = path_auto_export / fn_expected
                if not path_fn_expected.is_file():
                    logger.info(f'Renaming latest file from "{path_fn_new.name}" to "{path_fn_expected.name}"')
                    correct_fn = move_file(path_fn_new, path_fn_expected)

                    path_fn_new = path_fn_expected
                    if not path_fn_expected.is_file():
                        logger.warning(f'File rename failed')
                    else:
                        correct_fn = True
                else:
                    logger.warning(f'>>>> Expected shot no file already exists: {path_fn_expected.name}. '
                                   f'Not sure how to rename {fn_new}\nPulses saved: {saved_pulses} <<<<')
                    correct_fn = False

            else:
                logger.warning(f'>>>> Newest file is older than time of change to latest shot number. <<<<')
                logger.warning(f'File created at {t_mod_fn_new}. Shot state change at {t_shot_change}. '
                               f'dt={dt_file_since_shot_change:0.1f} < 0 ')
                correct_fn = False
        elif (dt_file_since_shot_change is None) or (dt_file_since_shot_change >= 0):
            # Name already correct and file age ok
            correct_fn = True
        else:
            logger.warning(f'File has correct name but is too old ({dt_file_since_shot_change} s): {path_fn_new}')
            correct_fn = False

        if correct_fn and path_fn_new.is_file() and (path_export_today is not None):
            dest = path_export_today / path_fn_new.name

            succes_move_today = move_file(path_fn_new, dest)
            if succes_move_today:
                logger.info(f'Moved latest file to {dest.parent} to preserve creation history')
                success_copy_back = copy_file(dest, path_fn_new)
                if success_copy_back:
                    logger.info(f'Copied new movie file back to {path_fn_new}')
            else:
                logger.warning(f'Failed to move latest file to {dest.parent} to preserve creation history')

            time.sleep(0.5)

            if (path_freia_export is not None) and (camera not in PROTECTION_CAMERAS):
                dest = path_freia_export / path_fn_new.name
                logger.info(f'Freia home ({FREIA_HOME_PATH.is_dir()}): {FREIA_HOME_PATH}')
                logger.info(f'Freia dest ({dest.is_dir()}): {dest}')
                dest_parent = dest
                for i in np.arange(4):
                    dest_parent = dest_parent.parent
                    logger.info(f'Freia dest parent ({dest_parent.is_dir()}): {dest_parent}')

                try:
                    success_move_freia = move_file(path_fn_new, dest)
                    if success_move_freia:
                        logger.info(f'Moved latest file to {dest.parent} to preserve creation history')
                        success_copy_back = copy_file(dest, path_fn_new)
                        if success_copy_back:
                            logger.info(f'Copied new movie file back to {path_fn_new}')
                    else:
                        logger.warning(f'Failed to move latest file to {dest.parent} to preserve creation history')

                except OSError as e:
                    logger.warning(f'Failed to move file to {path_freia_export}')
                    try:
                        path_fn_new.write_bytes(dest.read_bytes())  # for binary files
                        logger.info(f'Copied new movie file back to {path_fn_new}')
                    except Exception as e:
                        logger.warning(f'Failed to copy file to {path_freia_export}')
        elif not correct_fn:
            logger.warning(f'Didn\'t copy file as rename success = {success_rename}')
        else:
            logger.warning(f'New file does not exist: {path_fn_new}. Rename success = {success_rename}')
    return n_files


if __name__ == '__main__':
    fn = '~/data/movies/diagnostic_pc_transfer/next_mast_u_shot_no.csv'
    # fn = '~/ccfepc/T/tfarley/next_mast_u_shot_no.csv'
    auto_update_next_shot_file(fn_shot=fn, t_refresh=0.25, t_delay=2.5, n_print=40, organise_ircam_raw=False,
                               rit_intershot_job=True, rir_intershot_job=True)
    # monitor_uda_latest_shot()
    # update_next_shot_file(44140)