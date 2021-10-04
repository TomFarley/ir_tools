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

from ir_tools.automation.automation_tools import auto_update_next_shot_file

logger = logging.getLogger(__name__)
logger.propagate = False

fn = '~/ccfepc/T/tfarley/next_mast_u_shot_no.csv'

if __name__ == '__main__':
    auto_update_next_shot_file(fn_shot=fn, organise_ircam_raw=True, run_sched=False)