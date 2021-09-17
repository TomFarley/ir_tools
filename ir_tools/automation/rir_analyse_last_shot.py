#!/usr/bin/env python

"""


Created: 
"""

import logging, subprocess
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from fire.scripts.review_analysed_shots import review_latest_shots

logger = logging.getLogger(__name__)
logger.propagate = False

FPATH_RIR_JOB = '/home/tfarley/repos/ir_tools/ir_tools/automation/jobs/intershot_runs/rir_intershot_job.cmd'

def submit_rir_intershot_job():
    try:
        out = subprocess.run(['llsubmit', FPATH_RIR_JOB], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT).stdout.decode()
    except Exception as e:
        print(e)
    else:
        print('Submitted rir intershot job')
        print(out)
    # out = out.replace('\n', '<br>')
    # with open(FPATH_TOP_LOG_REMOTE, 'w') as f:
    #     f.write(out)


def rir_intershot():
    review_latest_shots(n_shots=2, camera='rir', copy_recent_shots=True)

if __name__ == '__main__':
    # submit_rit_intershot_job()  # recursive!
    rir_intershot()
    pass