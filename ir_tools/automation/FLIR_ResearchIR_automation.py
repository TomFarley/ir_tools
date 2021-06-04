
import os
import time as tm
import numpy as np
from datetime import datetime
from pathlib import Path

from ir_automation import (click, move, get_fns_and_dirs, copy_files, copy_dir, delete_files_in_dir,
    read_shot_number, write_shot_number)



date = datetime.now().strftime('%Y-%m-%d')
path_output = f'D:\\MAST-U_Operations\\AIR-FLIR_1\\{date}'
path_output = Path(path_output)

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
			# click(550,1070)    # position for full screen Altair

			# print('just clicked record')
			old_number_of_files = new_number_of_files
		else:
			pass
			# print('no need to click')

except KeyboardInterrupt:
	print('script terminated')
	pass




