
import os
import time as time
import numpy as np
from datetime import datetime
from pathlib import Path

from ir_automation import (click, move, get_fns_and_dirs, copy_files, copy_dir, delete_files_in_dir,
    read_shot_number, write_shot_number, filenames_in_dir)

date = datetime.now().strftime('%Y-%m-%d')
path_auto_export = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export')
path_output = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\{date}')
path_t_drive = Path(f'T:\\tfarley\\RIR\\')
path_t_drive_today = path_t_drive / date
path_local_today = path_auto_export.parent / date
fn_shot = path_t_drive / '../next_mast_u_shot_no.csv'

t_wait = 2

def automate_research_ir():

	print(f'\nMonitoring {path_output}')

	print(f"""Please ensure:
		- ResearchIR is configured to write movies to {path_output}
		- Red record button is active (as opposed to record settings)
		- The record button has been pressed manually so the camera starts in armed state.
		- ResearchIR is set to write ats files starting from the correct shot number""")

	print(f'Deleting previously exported files in {path_auto_export} (ideally from previous day)')
	delete_files_in_dir(path_auto_export, glob='*.ats')

	if not path_output.is_dir():
		path_output.mkdir(existsok=True)
		print(f'Created directory: {path_output}')

	f = filenames_in_dir(path_output)

	old_number_of_files = len(f)
	# print(f[0])

	try:
		while True:
			move(int(np.random.random()*10000),int(np.random.random()*10000))  # stop logout
			
			f = filenames_in_dir(path_output)
		
			new_number_of_files = len(f)

			print(f'{new_number_of_files} files. Waiting {t_wait} mins for next check {datetime.now()}')
			
			time.sleep(t_wait*60)
			
			# time.sleep(5*3)
			if new_number_of_files!=old_number_of_files:
				# for i in range(20):
				print(f'{new_number_of_files} files. New file present. Clicking record {datetime.now()}')
				click(360,55)
				# print('just clicked record')
				old_number_of_files = new_number_of_files
				time.sleep(0.5*60)
				print(f'Copying files to {path_local_today}')
				copy_files(path_auto_export, path_local_today)
				print(f'Copying files to {path_t_drive_today}')
				copy_files(path_auto_export, path_t_drive_today)
			else:
				pass
				print(f'{new_number_of_files} files. No need to click')

	except KeyboardInterrupt:
		print('script terminated')
		pass

if __name__ == '__main__':
	automate_research_ir()


