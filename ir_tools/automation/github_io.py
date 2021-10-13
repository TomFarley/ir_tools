#!/usr/bin/env python

"""


Created: 
"""

import logging
from pathlib import Path
import os
import subprocess

logger = logging.getLogger(__name__)
YES = 'SUCCESS'

def update_remote_log(fn_local_log, fn_remote_log):
    """ push top-level MWI log file to github """

    try:
        copy_log_tail_to_file(fn_local_log, fn_remote_log, n_lines=100)
        git_commit(fn_remote_log, message='auto-update')
        git_pull(fn_remote_log)
        git_push(fn_remote_log)
    except Exception as e:
        logger.info('Failed to update remote log ' + repr(e))
        return 1
    else:
        logger.info('Updated remote log: ' + YES)
        return 0

def git_commit(path_fn, message='auto-update', args=('-a',)):
    # -a to add file
    # -C run from starting directory
    proccess = subprocess.run(['git', '-C', os.path.dirname(path_fn), 'commit', *args, '-m', message, ],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, )
    logger.info(f'Git commit "{path_fn}", "{message}"')
    return proccess

def git_push(path_fn, args=('-q',), remote='origin', branch='main', ):
    """
    Use git CLI for saving credentials:
    https://stackoverflow.com/questions/6565357/git-push-requires-username-and-password
    Args:
        path_fn:
        args:
        remote:
        branch:

    Returns:

    """
    # -q quiet
    proccess = subprocess.run(['git', '-C', os.path.dirname(path_fn), 'push', *args, remote, branch],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, )
    logger.info(f'Git push "{path_fn}"')
    return proccess

def git_pull(path_fn, args=('-q',), remote='origin', branch='main', ):
    # -q quiet
    proccess = subprocess.run(['git', '-C', os.path.dirname(path_fn), 'pull', *args, remote, branch],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, )
    logger.info(f'Git push "{path_fn}"')
    return proccess

def copy_log_tail_to_file(fn_in, fn_out, n_lines=200):
    # update file
    if not Path(fn_in).is_file():
        logger.warning(f'Local log file does not exist: {fn_in}')
    if not Path(fn_out).is_file():
        logger.info(f'Remote log file does not exist: {fn_in}')

    out = subprocess.run(['tail', '-n', str(n_lines), fn_in], stdout=subprocess.PIPE, ).stdout.decode()
    out = out.replace('\n', '<br>')
    with open(fn_out, 'w') as f:
        f.write(out)
    logger.info(f'Copied tail from "{fn_in}" to "{fn_out}"')
    return out

if __name__ == '__main__':
    pass