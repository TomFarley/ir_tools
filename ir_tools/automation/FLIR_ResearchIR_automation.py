
import os, re
import time as time
import numpy as np
from datetime import datetime
from pathlib import Path

from ir_tools.automation.ir_automation import (click, move_mouse, get_fns_and_dirs, copy_files, copy_dir,
                                               delete_files_in_dir, read_shot_number, write_shot_number,
                                               filenames_in_dir, mkdir)
from ir_tools.automation import ir_automation

date = datetime.now().strftime('%Y-%m-%d')
path_auto_export = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export')
path_auto_export_backup = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export_backup')
# path_output = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\{date}')
path_output = path_auto_export
path_t_drive = Path(f'T:\\tfarley\\RIR\\')
path_t_drive_today = path_t_drive / date
path_freia = Path('H:\\data\\movies\\diagnostic_pc_transfer\\rir\\')
path_freia_today = path_freia / date
path_local_today = path_auto_export.parent / date
fn_shot = path_freia / '../next_mast_u_shot_no.csv'

t_update = 0.5
t_post_pulse = 2.5
n_print = 15

pixel_coords = {}
pixel_coords['record'] = (360, 55)

def automate_research_ir():

    print(f'\nMonitoring {path_output}')

    print(f"""Please ensure:
        - ResearchIR is configured to write movies to {path_output}
        - Red record button is active (as opposed to record settings)
        - The record button has been pressed manually so the camera starts in armed state.
        - ResearchIR is set to write ats files starting from the correct shot number
        - Screen resolution is set to 1920 x 1080 ??? not 1200 ???""")

    print(f'Transfering previously exported files in {path_auto_export} to {path_auto_export_backup} (ideally from previous day)')
    copy_files(path_auto_export, path_auto_export_backup)
    delete_files_in_dir(path_auto_export, glob='*.ats')

    mkdir(path_local_today)
    mkdir(path_freia_today)
    # mkdir(path_t_drive_today)

    fns_autosaved = filenames_in_dir(path_auto_export)

    old_number_of_files = len(fns_autosaved)
    # print(f[0])
    shot_number = read_shot_number(fn_shot)  # Keep reading file incase file on T drive updated
    print(f'Next shot is {shot_number}')

    print(f'Updates will be printed every {n_print*t_update} mins, with file checks every {t_update} mins')

    try:
        n = 0
        while True:
            move_mouse(int(np.random.random()*10000),int(np.random.random()*10000))  # stop logout

            fns_autosaved = filenames_in_dir(path_auto_export)
            new_number_of_files = len(fns_autosaved)

            shot_number_prev = shot_number
            shot_number = read_shot_number(fn_shot)  # Keep reading file incase file on T drive updated
            if shot_number != shot_number_prev:
                print(f'{datetime.now()}: Read updated shot number "{shot_number}" from {fn_shot}')

            # print(f'{new_number_of_files} files. Waiting {t_wait} mins for next check {datetime.now()}')

            # time.sleep(5*3)
            if new_number_of_files!=old_number_of_files:
                # for i in range(20):
                print(f'{datetime.now()}: {new_number_of_files} files. New file present. Waiting {t_post_pulse} min for clock pulse train to finish.')

                i_order, ages, fns_sorted = ir_automation.sort_files_by_age(fns_autosaved, path=path_auto_export)
                pattern = '(\d+).ats'
                saved_pulses = []
                for fn in fns_sorted:
                    m = re.match(pattern, fn)
                    pulse = int(m.groups()[0]) if m else None
                    saved_pulses.append(pulse)

                print(f'fns: {fns_sorted}')
                print(f'pulses: {saved_pulses}')
                print(f'ages: {ages}')
                if new_number_of_files > 0:
                    fn_new, age_fn_new, shot_fn_new = Path(fns_sorted[0]), ages[0], saved_pulses[0]
                    print(f'{datetime.now()}: File "{fn_new}" for shot {shot_fn_new} ({shot_number} expected) saved '
                          f'{age_fn_new:0.1f} s ago')

                    if shot_fn_new != shot_number:
                        fn_expected = path_auto_export / f'0{shot_number}.ats'
                        if (age_fn_new > t_update*60+2) and (shot_number-fn_shot_new == 1):
                        	print(f'Not renaming shot as script seems to have been delayed acting')
                        elif not fn_expected.is_file():
                            print(f'{datetime.now()}: Renaming latest file from "{fn_new.name}" to "{fn_expected.name}"')
                            (path_auto_export / fn_new).rename(fn_expected)
                        else:
                            print(f'Expected shot no file already exists: {fn_expected}. Not sure how to rename {fn_new}\n'
                                  f'Pulses saved: {saved_pulses}')

                time.sleep(t_post_pulse*60)
                print(f'{datetime.now()}: Clicking record ({pixel_coords["record"]})')
                click(*pixel_coords["record"])

                # print('just clicked record')
                old_number_of_files = new_number_of_files

                # print(f'Copying files to {path_local_today}')
                copy_files(path_auto_export, path_local_today)
                print(f'Copying files to {path_freia_today}')
                copy_files(path_local_today, path_freia_today)
            else:
                pass
                if (n % n_print) == 0:
                    print(f'{datetime.now()}: {new_number_of_files} files. No need to click. Waiting {t_update} mins for next check. (n={n})')
                time.sleep(t_update*60)
                n += 1
    except KeyboardInterrupt:
        print('script terminated')
        pass

if __name__ == '__main__':
    automate_research_ir()


