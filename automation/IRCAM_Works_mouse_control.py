import os, shutil
import time 
import numpy as np
from datetime import datetime
from copy import copy
import clipboard
from pynput.keyboard import Key, Controller
from pathlib import Path
import csv

from ir_automation import (click, get_fns_and_dirs, copy_files, copy_dir, delete_files_in_dir,
    read_shot_number, write_shot_number)

keyboard = Controller()

# shot_number = 44103
    
# path_hdd_out = 'D:\\IRVB\\2021-05-20'
path_hdd_out = Path(r'D:\\MAST-U\LWIR_IRCAM1_HM04-A\Operations\To_be_exported')
path_auto_export = Path(f'D:\\MAST-U\\LWIR_IRCAM1_HM04-A\\Operations\\2021-1st_campaign\\auto_export')
path_t_drive = Path(f'T:\\tfarley\\RIT\\')
path_todays_pulses = path_auto_export.parent / datetime.now().strftime('%Y-%m-%d')
fn_shot = path_t_drive / '../next_mast_u_shot_no.csv'

n_min_wait_dir_refresh = 0.25
n_min_wait_post_pulse = 2

# Mouse coords from top left (1920 x 1080) -> (860)
# record_button_pixel_coords = np.array([500, 890], dtype=int) #  ??
pixel_coords = {'record_button': [580, 766],  #  1920 x 1080, not full screen
                'file': [15, 32],
                'export': [20, 170],
                'int16_seq': [220, 220],
                'save': [400, 400],
                'rename': [50, 400]
                }
for key, value in pixel_coords.items():
    pixel_coords[key] = np.array(value, dtype=int)


# old_number_of_files = np.nan

def check_for_armed_file(fns):
    armed_fn = None
    for fn in fns:
        if '.space' in fn:
            armed = True
            # print(f'Camera IS in armed state ({fn})')
            break
    else:
        armed = False
        # print(f'Camera out of armed state')
    return armed, armed_fn

def export_movie(shot_number):
    clipboard.copy(str(shot_number))
    
    click(*tuple(pixel_coords['file']))

    for i in np.arange(8):
        keyboard.press(Key.down)
        time.sleep(0.2)
    keyboard.press(Key.right)
    for i in np.arange(2):
        keyboard.press(Key.down)
        time.sleep(0.2)
    keyboard.press(Key.enter)
    time.sleep(1)

    for char in str(shot_number):
        keyboard.press(char)
        time.sleep(0.1)


    time.sleep(0.5)
    keyboard.press(Key.enter)
    time.sleep(3)
    fns, dirs = get_fns_and_dirs(path_auto_export)
    if f'{shot_number}.RAW' in fns:
        print(f'Exported current movie to {shot_number}.RAW')
        return True
    else:
        print(f'Failed to export RAW movie to {path_auto_export}: {fns}')
        return False


def auto_trigger(path_hdd_out):

    shot_number = read_shot_number(fn_shot)

    print(f"""\nRunning automated IRCAM Works recorder. Please ensure:
              1) The IRCAM Works software is maximised
              2) "HDD recording" is set to record to "{path_hdd_out}"
              3) The camera is set to "Trigger: yes" 
              4) The live view of the camera is set to display in 'camera units' (required for raw export)
              5) No windows are blocking the red record button
              6) The next shot number is "{shot_number}" (update in script if incorrect)
              7) The screen resolution is 1920 x 1080\n""")

    fns, dirs_top = get_fns_and_dirs(path_hdd_out)
    n_dirs_initial = len(dirs_top)

    print('Deleting exported files from previous day')
    delete_files_in_dir(path_auto_export, glob='*.RAW')

    print(f'Initial numnber of movie dirs in path: {n_dirs_initial}')

    armed = False
    post_pulse = False

    try:
        while True:
            shot_number_prev = shot_number
            shot_number = read_shot_number(fn_shot)  # Keep reading file incase file on T drive updated
            if shot_number != shot_number_prev:
                print(f'Read updated shot number "{shot_number}" from {fn_shot}')

            # move(int(np.random.random()*10000),int(np.random.random()*10000)) # Stop lock screen
            previous_armed_state = armed
            
            fns, dirs_top = get_fns_and_dirs(path_hdd_out)
            armed, armed_fn = check_for_armed_file(fns)
            
            n_dirs = len(dirs_top)
            new_number_of_files = len(fns)

            # time.sleep(5*3)
            if not armed:
                print(f'\nCamera NOT in armed state: {datetime.now()}')  #\n{fns}')
                if previous_armed_state is True:
                    post_pulse = True
                    time.sleep(6)  # Wait for recording to finish
                    
                    status = export_movie(shot_number)
                    if status is True:
                        copy_files(path_auto_export, path_todays_pulses)
                        copy_dir(path_todays_pulses, path_t_drive)
                    
                    print(f'Waiting {n_min_wait_post_pulse} mins after shot {shot_number} before re-arming to ensure pulse train has finished from previous shot: {datetime.now()}')
                    time.sleep(n_min_wait_post_pulse*60) # you need to leave this pause when it detects that the record is done. otherwise it clicks too early.
                    post_pulse = False
                    shot_number += 1    
                    write_shot_number(fn_shot, shot_number)          
                
                print(f'Clicking record button at {tuple(pixel_coords["record_button"])} ({n_dirs} dirs) {datetime.now()}')
                click(*tuple(pixel_coords["record_button"]))  # click record button
                time.sleep(0.5)

                fns, dirs_top = get_fns_and_dirs(path_hdd_out)
                armed, armed_fn = check_for_armed_file(fns)
                n_dirs = len(dirs_top)
                print(f'Current number of movie dirs in path: {n_dirs}')
                if armed:
                    print(f'\n========== {shot_number} ==========\nSuccessfully armed camera for shot {shot_number} with click to {tuple(pixel_coords["record_button"])}: {datetime.now()}\n')
                    time.sleep(n_min_wait_post_pulse*60)
                else:
                    print(f'\n\nWARNING: FAILED to re-arm camera: {datetime.now()}\n')
            else:
                if previous_armed_state is False:
                    print(f'Camera armed for shot {shot_number} - no action required: {datetime.now()}')
                    post_pulse = False
                
                # print(f'Waiting {n_min_wait_dir_refresh} mins for next status (armed={armed}) check: {datetime.now()}')
                time.sleep(n_min_wait_dir_refresh*60)

            # print(f'Waiting {n_min_wait_dir_refresh} mins before next directory check')
            # fns

    except KeyboardInterrupt:
        print(f'script terminated: {datetime.now()}')
        pass


if __name__ == '__main__':
    auto_trigger(path_hdd_out)