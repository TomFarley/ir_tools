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


logger = logging.getLogger(__name__)
logger.propagate = False

def read_tiff(path_fn):
    data = plt.imread(path_fn)
    return data

def read_seq(path_fn):
    import flirpy
    from flirpy.io import seq
    splitter = seq.splitter(str(path_fn.parent))#, width=, height=)
    splitter.process([str(path_fn)])
    data = flirpy.io.seq
    return data


if __name__ == '__main__':
    pulse = 44495
    path = Path(f'/home/tfarley/data/movies/mast_u/{pulse}/split_test/')

    fn = f'0{pulse}.seq'
    data = read_seq(path / fn)

    fn = f'0{pulse}.tif'
    data = read_tiff(path / fn)
    pass