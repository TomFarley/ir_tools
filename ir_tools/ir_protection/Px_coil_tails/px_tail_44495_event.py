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

from ir_tools.ir_protection import temporal_data

def plot_max_T_trace(data):
    print(data)
    data.loc[:, 'reltime'] -= 8.6
    data = data.set_index('reltime')

    fig, ax = plt.subplots()
    t_max = data['Function 1 [C]']
    t_max.plot(ax=ax)
    ax.set_xlim(0, 2.5)
    ax.set_ylabel(r'$T_{max} [^\circ$C]')
    ax.set_xlabel(r'$t$ [s]')
    plt.show()

if __name__ == '__main__':
    pulse = 44495
    path = Path(f'/home/tfarley/data/movies/mast_u/{pulse}/')

    fn = f'max_T_trace-{pulse}.csv'
    data = temporal_data.read_temporal_csv(path / fn)
    plot_max_T_trace(data)