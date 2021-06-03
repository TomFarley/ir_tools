
import os
import time as tm
import numpy as np
from datetime import datetime
from pathlib import Path

from ir_automation import (click, move, get_fns_and_dirs, copy_files, copy_dir, delete_files_in_dir,
    read_shot_number, write_shot_number)

date = datetime.now().strftime('%Y-%m-%d')
path_auto_export = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\auto_export')
path_output = Path(f'D:\\MAST-U_Operations\\AIR-FLIR_1\\{date}')
path_t_drive = Path(f'T:\\tfarley\\RIR\\')
path_t_drive_today = path_t_drive / date
path_local_today = path_auto_export.parent / date
fn_shot = path_t_drive / '../next_mast_u_shot_no.csv'

if not path_output.is_dir():
	path_output.mkdir(existsok=True)
	print(f'Created directory: {path_output}')

print(f'\nMonitoring {path_output}')

print(f"""Please ensure:
	- ResearchIR is configured to write movies to {path_output}
	- Red record button is active (as opposed to record settings)
	- ResearchIR is set to write ats files starting from the correct shot number""")

if not path_output.is_dir():
	path_output.mkdir()
	print(f'Created new directory: {path_output}')

f = []
for (dirpath,dirnames,filenames) in os.walk(path_output):
	f.append(filenames)
	break

old_number_of_files = len(f[0])
# print(f[0])

try:
	while True:
		move(int(np.random.random()*10000),int(np.random.random()*10000))
		f = []
		for (dirpath,dirnames,filenames) in os.walk(path_output):
			f.append(filenames)
			break
	
		new_number_of_files = len(f[0])
		print(f'Waiting 3 mins for next check {datetime.now()}')
		tm.sleep(2*60)
		# tm.sleep(5*3)
		if new_number_of_files!=old_number_of_files:
			# for i in range(20):
			print(f'Clicking record {datetime.now()}')
			click(360,55)
			# print('just clicked record')
			old_number_of_files = new_number_of_files
			time.sleep(0.5*60)
			copy_files(path_auto_export, path_local_today)
			copy_files(path_auto_export, path_t_drive_today)
		else:
			pass
			# print('no need to click')

except KeyboardInterrupt:
	print('script terminated')
	pass




