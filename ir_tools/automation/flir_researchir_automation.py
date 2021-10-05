
import os, re, logging
import time as time
import numpy as np
from datetime import datetime
from pathlib import Path

from ir_tools.automation.automation_tools import (click_mouse, move_mouse, get_fns_and_dirs, copy_files, copy_dir,
                                                  delete_files_in_dir, read_shot_number, write_shot_number,
                                                  filenames_in_dir, mkdir)
from ir_tools.automation import automation_tools
from ir_tools.automation.automation_settings import FPATH_LOG

PATH_AUTO_EXPORT = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export')
PATH_T_DRIVE = Path(f'T:\\tfarley\\RIR\\')
PATH_FREIA = Path('H:\\data\\movies\\diagnostic_pc_transfer\\rir\\')

date = datetime.now().strftime('%Y-%m-%d')

path_auto_export_backup = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export_backup')
# path_output = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\{date}')
path_output = PATH_AUTO_EXPORT
path_t_drive_today = PATH_T_DRIVE / date
path_freia_today = PATH_FREIA / date
path_local_today = PATH_AUTO_EXPORT.parent / date

fn_shot = PATH_FREIA / '../next_mast_u_shot_no.csv'

T_UPDATE = 0.5
T_POST_PULSE = 2.5
N_PRINT = 15

PIXEL_COORDS = {}
PIXEL_COORDS['record'] = (360, 55)

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

def automate_research_ir():

    print(f'\nMonitoring {path_output}')

    print(f"""Please ensure:
        - ResearchIR is configured to write movies to {path_output}
        - Red record button is active (as opposed to record settings)
        - The record button has been pressed manually so the camera starts in armed state.
        - ResearchIR is set to write ats files starting from the correct shot number
        - Screen resolution is set to 1920 x 1080 ??? not 1200 ???""")

    print(
        f'Transfering previously exported files in {PATH_AUTO_EXPORT} to {path_auto_export_backup} (ideally from previous day)')
    copy_files(PATH_AUTO_EXPORT, path_auto_export_backup)
    delete_files_in_dir(PATH_AUTO_EXPORT, glob='*.ats')

    mkdir(path_local_today)
    mkdir(path_freia_today)
    # mkdir(path_t_drive_today)

    fns_autosaved = filenames_in_dir(PATH_AUTO_EXPORT)

    old_number_of_files = len(fns_autosaved)
    # print(f[0])
    shot_number = read_shot_number(fn_shot)  # Keep reading file incase file on T drive updated
    print(f'Next shot is {shot_number}')

    print(f'Updates will be printed every {N_PRINT*T_UPDATE} mins, with file checks every {T_UPDATE} mins')

    try:
        n = 0
        while True:
            move_mouse(int(np.random.random()*10000),int(np.random.random()*10000))  # stop logout

            fns_autosaved = filenames_in_dir(PATH_AUTO_EXPORT)
            new_number_of_files = len(fns_autosaved)

            shot_number_prev = shot_number
            shot_number = read_shot_number(fn_shot)  # Keep reading file incase file on T drive updated
            if shot_number != shot_number_prev:
                print(f'{datetime.now()}: Read updated shot number "{shot_number}" from {fn_shot}')

            # print(f'{new_number_of_files} files. Waiting {t_wait} mins for next check {datetime.now()}')

            # time.sleep(5*3)
            if new_number_of_files!=old_number_of_files:
                # for i in range(20):
                print(
                    f'{datetime.now()}: {new_number_of_files} files. New file present. Waiting {T_POST_PULSE} min for clock pulse train to finish.')

                i_order, ages, fns_sorted = automation_tools.sort_files_by_age(fns_autosaved, path=PATH_AUTO_EXPORT)
                saved_shots = automation_tools.shot_nos_from_fns(fns_sorted, pattern='(\d+).ats')

                print(f'fns: {fns_sorted}')
                print(f'pulses: {saved_shots}')
                print(f'ages: {ages}')
                if new_number_of_files > 0:
                    fn_new, age_fn_new, shot_fn_new = Path(fns_sorted[0]), ages[0], saved_shots[0]
                    print(f'{datetime.now()}: File "{fn_new}" for shot {shot_fn_new} ({shot_number} expected) saved '
                          f'{age_fn_new:0.1f} s ago')

                    if shot_fn_new != shot_number:
                        fn_expected = PATH_AUTO_EXPORT / f'0{shot_number}.ats'
                        if (age_fn_new > T_UPDATE*60+2) and (shot_number-shot_fn_new == 1):
                            print(f'Not renaming shot as script seems to have been delayed acting')
                        elif not fn_expected.is_file():
                            print(f'{datetime.now()}: Renaming latest file from "{fn_new.name}" to "{fn_expected.name}"')
                            (PATH_AUTO_EXPORT / fn_new).rename(fn_expected)
                        else:
                            print(f'Expected shot no file already exists: {fn_expected}. Not sure how to rename {fn_new}\n'
                                  f'Pulses saved: {saved_shots}')

                time.sleep(T_POST_PULSE * 60)
                print(f'{datetime.now()}: Clicking record ({PIXEL_COORDS["record"]})')
                click_mouse(*PIXEL_COORDS["record"])

                # print('just clicked record')
                old_number_of_files = new_number_of_files

                # print(f'Copying files to {path_local_today}')
                copy_files(PATH_AUTO_EXPORT, path_local_today)
                print(f'Copying files to {path_freia_today}')
                copy_files(path_local_today, path_freia_today)
            else:
                pass
                if (n % N_PRINT) == 0:
                    print(
                        f'{datetime.now()}: {new_number_of_files} files. No need to click. Waiting {T_UPDATE} mins for next check. (n={n})')
                time.sleep(T_UPDATE * 60)
                n += 1
    except KeyboardInterrupt:
        print('script terminated')
        pass

def start_recording_research_ir(pixel_coords, camera, logger=None):
    from pynput.keyboard import Key, Controller
    keyboard = Controller()
    if logger is not None:
        logger.info(f'Start recording for "{camera}" camera. Clicking on image {pixel_coords} and pressing F5.')
    try:
        automation_tools.click_mouse(*pixel_coords)
    except Exception as e:
        if logger is not None:
            logger.excetion(f'Failed to start Research IR recording for "{camera}" with click at {pixel_coords}')
        else:
            print(f'Failed to start Research IR recording for "{camera}" with click at {pixel_coords}')
    keyboard.press(Key.f5)
    keyboard.press(Key.ctrl)  # Display mouse location
    keyboard.release(Key.ctrl)

if __name__ == '__main__':
    automate_research_ir()