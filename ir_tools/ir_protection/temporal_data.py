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

from ir_tools.ir_protection.FLIR_AX5 import read_flir_ax5_movie

logger = logging.getLogger(__name__)
logger.propagate = False


def read_temporal_csv(path_fn):
    from fire.interfaces.io_basic import read_csv
    data = read_csv(path_fn)
    return data


