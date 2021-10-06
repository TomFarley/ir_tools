#!/usr/bin/env python

"""


Created: 
"""

import logging

from ir_tools.automation.automation_settings import FPATH_LOG

# logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
# logger.propagate = False

fhandler = logging.FileHandler(FPATH_LOG)
shandler = logging.StreamHandler()
[i.setLevel('INFO') for i in [logger, fhandler, shandler]]
formatter = logging.Formatter('%(asctime)s - %(message)s')
fhandler.setFormatter(formatter)
shandler.setFormatter(formatter)
logger.addHandler(fhandler)
logger.addHandler(shandler)

if __name__ == '__main__':
    pass