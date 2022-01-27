#!/usr/bin/env python

"""


Created: 
"""

import logging as _logging

_logging.basicConfig()
logger_ir_tools = _logging.getLogger(__name__)
# logger.propagate = False

from . import automation
from . import data_formats

if __name__ == '__main__':
    pass