#!/usr/bin/env python

"""


Created: 
"""

import logging
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from fire.plugins.movie_plugins import ipx, uda

logger = logging.getLogger(__name__)
logger.propagate = False

def ipx_write_example():
    pulse = 29852
    path_fn_ipx = f'test_{pulse}.ipx'
    frame_nos, frame_times, movie_data = uda.read_movie_data(pulse, 'rir')
    header_dict = uda.read_movie_meta(pulse, 'rir')
    header_dict['frame_times'] = frame_times
    verbose = True
    ipx.write_ipx_with_mastmovie(path_fn_ipx, movie_data, header_dict, verbose)

if __name__ == '__main__':
    ipx_write_example()
    pass