#!/usr/bin/env python

"""


Created: 
"""

import logging, time
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from ir_tools.automation import automation_tools
from ir_tools.automation.automation_tools import click_mouse

logger = logging.getLogger(__name__)
logger.propagate = False

def check_screen_change():
    try:
        from PIL import ImageChops  # $ pip install pillow
        from pyscreenshot import grab  # $ pip install pyscreenshot
    except ImportError as e:
        logger.warning(f'Failed to import libraries for {check_screen_change}: {e}')
        return

    #	checking how many pixels change in two screenshots taken shortly apart
    im1 = grab()
    time.sleep(0.5)
    im2 = grab()
    diff = ImageChops.difference(im1, im2)
    diff1 = diff.getdata()

    changed_pixels = 0
    for i in range(np.shape(diff1)[0]):
        if diff1[i] != (0, 0, 0):
            changed_pixels += 1

    return changed_pixels

def switch_to_internal_trigger():
    # exit when new pulse initiated
    print('start switch to internal trigger')
    automation_tools.click_mouse(195, 1125)  # select the "camera" sheet
    time.sleep(0.1)
    automation_tools.click_mouse(185, 1070)  # select internal clocks
    print('back to internal trigger')

def start_recording():
    time.sleep(10)  # time to allow to finish finish saving files
    print('clicking start recording')
    # click(360,55)	# position for ResearchIR
    # click(80,490)	# position for minimised Altair
    click_mouse(320, 1125)  # select the "recorder" sheet
    time.sleep(0.1)
    click_mouse(550, 1070)  # position for full screen Altair, start record
    print('new recording started')
    # print('wait '+str(min_to_wait)+'min')

    time.sleep(0.1)
    print('reset of visual range')
    click_mouse(640, 60)  # reset the range of the frame visualisation
    print('visual range reset')

    time.sleep(10)  # time to allow to finish resetting the range
    # If camera is still in external clock image will not refresh - few pixels change
    changed_pixels = check_screen_change()
    if (changed_pixels is None) or (changed_pixels > 1000):  # arbitrary threshold for camera in internal clocks
        print(str(
            changed_pixels) + ' pixels changed\ncamera assumed to be in internal clocks\ntherefore changed to external')
        click_mouse(195, 1125)  # select the "camera" sheet
        time.sleep(0.1)
        click_mouse(185, 1070)  # select external clocks
    else:
        print('only ' + str(changed_pixels) + ' pixels changed, so no action taken')
    # camera left in record activated and external clocks

    time.sleep(0.1)

def handle_abort():
    print('Abort detected')
    print('clicking stop recording')
    click_mouse(320, 1125)  # select the "recorder" sheet
    time.sleep(0.1)
    click_mouse(600, 1070)  # position for full screen Altair, stop record
    print('recording stopped')

    # now the number of the shot inside altair should advance by one

    print('clicking start recording')
    click_mouse(320, 1125)  # select the "recorder" sheet
    time.sleep(0.1)
    click_mouse(550, 1070)  # position for full screen Altair, start record
    print('new recording started')
    # print('wait '+str(min_to_wait)+'min')

    time.sleep(0.1)
    print('reset of visual range')
    click_mouse(640, 60)  # reset the range of the frame visualisation
    print('visual range reset')

    time.sleep(10)
    changed_pixels = check_screen_change()
    if (changed_pixels is not None) and (changed_pixels > 1000):  # arbitrary threshold for camera in internal clocks
        print(str(
            changed_pixels) + ' pixels changed\ncamera assumed to be in internal clocks\ntherefore changed to external')
        click_mouse(195, 1125)  # select the "camera" sheet
        time.sleep(0.1)
        click_mouse(185, 1070)  # select external clocks
    else:
        print('only ' + str(changed_pixels) + ' pixels changed, so no action taken')
    # camera left in record activated and external clocks


if __name__ == '__main__':
    pass