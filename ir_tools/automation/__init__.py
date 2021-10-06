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
logger.addHandler(shandler)
logger.addHandler(fhandler)

if __name__ == '__main__':
    # Set logging level for console output handler propagated throughout fire package
    handlers = logger.handlers
    for handler in handlers:
        print(f'logging handler {handler} set to level: {handler.level}')

    if len(handlers) > 0:
        stream_handler = handlers[0]
    else:
        logger.warning(f'Failed to set up stream handler')

    logger.setLevel(logging.DEBUG)
    print(f'parent logger {logger_fire} set to level: {logger_fire.level}')
    pass