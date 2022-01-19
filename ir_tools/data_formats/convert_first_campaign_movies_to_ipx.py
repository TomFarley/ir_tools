#!/usr/bin/env python

"""


Created: 
"""

import logging
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from fire.interfaces import io_basic
from ir_tools.data_formats import ircam_raw_movies_to_ipx, flir_ats_movie_to_ipx

logger = logging.getLogger(__name__)

path_pre_ipx_archive = Path('/projects/SOL/Data/Cameras/IR')
path_ipx_archive = Path('/projects/SOL/Data/Cameras/IR/ipx')

def convert_ircam_raw_files_archive_to_ipx(shots=None, path=None):
    path_raw_root = path_pre_ipx_archive / 'RIT'  #  Path('~/data/movies/mast_u/').expanduser()

    shots_converted = []

    date_dirs = sorted(path_raw_root.glob("*/"))

    for date_dir in date_dirs:
        print(date_dir)
        path_fns_raw = sorted(date_dir.glob('*.raw'))
        path_fns_raw += sorted((date_dir.glob('*.RAW')))
        print(path_fns_raw)

        for path_fn_raw in path_fns_raw:
            m = re.search('(\d{5})\.', str(path_fn_raw.name))
            if m is not None:
                shot = int(m.groups()[0])
            else:
                logger.warning(f'Failed to extract pulse number from raw file: {path_fn_raw}')
                continue

            if (shots is not None) and (shot not in shots):
                continue

            fn_meta = f'rit0{shot}_meta.json'

            meta_data_dict, n_frames, image_shape = ircam_raw_movies_to_ipx.look_up_lwir1_meta_data(shot)
            ircam_raw_movies_to_ipx.generate_json_meta_data_file_for_ircam_raw(path_fn_raw.parent, path_fn_raw.name,
                                            n_frames=n_frames, image_shape=image_shape, meta_data_dict=meta_data_dict)

            path_fn_ipx = path_ipx_archive / f'0{str(shot)[:2]}/{shot}' / f'rit0{shot}.ipx'
            io_basic.mkdir(path_fn_ipx, depth=3)

            ircam_raw_movies_to_ipx.generate_ipx_file_from_ircam_raw_movie(path_fn_raw=path_fn_raw,
                                        path_fn_ipx=path_fn_ipx, pulse=shot, verbose=True, plot_check=True)
            shots_converted.append(shot)
            break

    logger.info(f'Converted {len(shots_converted)} to ipx: {shots_converted}')

def convert_specific_ircam_raw_pulses_to_ipx(pulses=None, path=None):
    path_raw_root = Path('~/data/movies/mast_u/').expanduser()
    if pulses is None:
        pulses = pulses[:1]  # tmp
        pulses = list(sorted([p.name for p in path_raw_root.glob('[!.]*')]))
        pulses = [44677, 44683]
        pulses = [44613]
    if path is not None:
        path = Path(path)

    print(pulses)

    for pulse in pulses:
        path = path_raw_root / f'{pulse}/rit/'

        fn_raw = f'rit_{pulse}.raw'
        fn_meta = f'rit_{pulse}_meta.json'
        fn_ipx = f'rit0{pulse}.ipx'

        if not (path/fn_raw).is_file():
            logger.warning(f'Raw file does not exist for pulse {pulse}: {fn_raw}')
            continue

            ircam_raw_movies_to_ipx.generate_ipx_file_from_ircam_raw_movie(path / fn_raw, path / fn_ipx, pulse=pulse)


def convert_ats_files_archive_to_ipx(pulses=None, path_in=None, date=None, copy_ats_file=False, fn_ats='0{pulse}.ats',
                                     fn_meta='/home/tfarley/data/movies/mast_u/rir_ats_files/rir_meta.json',
                                     n_files=None):
    from fire.interfaces.interfaces import locate_file
    from fire.interfaces.io_utils import filter_files, filter_files_in_dir
    path_root = Path('~/data/movies/mast_u/').expanduser()

    success, failed = [], []

    if (date is None) or (date == 'today'):
        date = datetime.now().strftime('%Y-%m-%d')

    if path_in is not None:
        path_in = Path(str(path_in).format(date=date)).expanduser()
    else:
        path_in = path_root / date

    print(f'Path_in: {path_in}')
    io_basic.copy_file(fn_meta, path_in, mkdir_dest=False, verbose=True, overwrite=True)

    if pulses is None:
        pulses = list(reversed(sorted([p.stem for p in path_in.glob('[!.]*')])))
        # pulses = [44677, 44683]
        # pulses = [44613]
        # pulses = pulses[:1]  # tmp

    print(f'Converting ats files for first "{n_files}" pulses to ipx from {pulses}')

    n_converted = 0
    for pulse in pulses:

        try:
            pulse = re.match('.*0?(\d{5})', str(pulse)).groups()[0]
            pulse = int(pulse)
        except Exception as e:
            print(f'Skipping file stem "{pulse}" in {path_in}')
            continue
        # path_in = path_root / f'rir_ats_files/'  # (\d4-\d2-\d2)/'
        path_out = path_root / f'{pulse}/rir/'

        fn_ats_formatted = fn_ats.format(pulse=pulse, shot=pulse)
        # fn_ats = f'rir_{pulse}.ats'
        # for path in path_in.glob('*'):
        #     fn_ats = path / f'rir_{pulse}.ats'

        fn_meta = f'rir_meta.json'
        fn_ipx = f'rir0{pulse}.ipx'

        if not (path_in / fn_ats_formatted).is_file():
            logger.warning(f'FLIR ats file does not exist for pulse {pulse}: {fn_ats}')
            continue

        path_fn_ats = path_in / fn_ats_formatted
        path_fn_ipx = path_out / fn_ipx
        try:
            flir_ats_movie_to_ipx.generate_ipx_file_from_flir_ats_movie(path_fn_ats, path_fn_ipx, pulse=pulse, plot_check=False)
        except IndexError as e:
            logger.exception(f'Failed to convert ats file to ipx for shot {pulse}')
            failed.append(pulse)
        else:
            success.append(pulse)

        if copy_ats_file:
            io_basic.copy_file(path_fn_ats, Path(path_fn_ipx).with_suffix('.ats'), overwrite=True, verbose=True)
            io_basic.copy_file(path_fn_ats.with_name(fn_meta), Path(path_fn_ipx).parent, overwrite=True,
                               raise_exceptions=False, verbose=True)
        n_converted += 1
        if (n_files is not None) and (n_converted >= n_files):
            break
    print(f'Successfully created ipx files for pulses {success}, failed for {failed}')

if __name__ == '__main__':
    convert_ircam_raw_files_archive_to_ipx()
    pass