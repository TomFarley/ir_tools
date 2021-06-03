import win32api,win32con
import os
import time as tm
import numpy as np
from datetime import datetime
from pathlib import Path

def click(x,y):
	win32api.SetCursorPos((x,y))
	win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
	win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)

def move(x,y):
	win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE,x,y,0,0)

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
			# print('just clicked record')
			old_number_of_files = new_number_of_files
		else:
			pass
			# print('no need to click')

except KeyboardInterrupt:
	print('script terminated')
	pass




