
import os
import time as time
import numpy as np
from datetime import datetime
from pathlib import Path

from ir_automation import (click, move_mouse, get_fns_and_dirs, copy_files, copy_dir, delete_files_in_dir,
    read_shot_number, write_shot_number, filenames_in_dir, mkdir)

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
fn_shot = path_t_drive / '../next_mast_u_shot_no.csv'

t_update = 0.5
t_post_pulse = 2.5
n_print = 15

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

	if not path_local_today.is_dir():
		path_local_today.mkdir()  # existsok=True)
		print(f'Created directory: {path_local_today}')
	if not path_t_drive_today.is_dir():
		path_t_drive_today.mkdir()  # existsok=True)
		print(f'Created directory: {path_local_today}')
	if not path_freia_today.is_dir():
		path_freia_today.mkdir()  # existsok=True)
		print(f'Created directory: {path_freia_today}')

	f = filenames_in_dir(path_auto_export)

	old_number_of_files = len(f)
	# print(f[0])

	print(f'Updates will be printed every {n_print*t_update} mins, with file checks every {t_update} mins')

	try:
		n = 0
		while True:
			move_mouse(int(np.random.random()*10000),int(np.random.random()*10000))  # stop logout

			f = filenames_in_dir(path_auto_export)

			new_number_of_files = len(f)

			# print(f'{new_number_of_files} files. Waiting {t_wait} mins for next check {datetime.now()}')

			# time.sleep(5*3)
			if new_number_of_files!=old_number_of_files:
				# for i in range(20):
				print(f'{datetime.now()}: {new_number_of_files} files. New file present. Waiting {t_post_pulse} min for clock pulse train to finish.')
				
				time.sleep(t_post_pulse*60)
				print(f'{datetime.now()}: Clicking record')
				click(360,55)
				
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


