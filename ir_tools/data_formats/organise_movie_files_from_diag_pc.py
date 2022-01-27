#!/usr/bin/env python

"""


Created: 
"""

import logging
from pathlib import Path
from copy import copy
from datetime import datetime, timedelta

from fire.interfaces import io_basic
from fire.misc.utils import make_iterable
from ir_tools.data_formats.ircam_raw_movies_to_ipx import (generate_ipx_file_from_ircam_raw_movie)
from ir_tools.data_formats.convert_first_campaign_movies_to_ipx import generate_json_movie_meta_data_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logger.propagate = False


def organise_ircam_raw_files(path_in='/home/tfarley/data/movies/diagnostic_pc_transfer/{date}/',
                             fn_in='(\d+).RAW', fn_in_group_keys=('pulse',), date='today',
                             path_out='~/data/movies/mast_u/{pulse}/{camera}/', fn_raw_out='{camera}_{pulse}.raw',
                             fn_meta='{camera}_{pulse}_meta.json', fn_ipx_format='rit0{pulse}.ipx',
                             pulse_whitelist=None, pulse_blacklist=None,
                             meta=None, camera_settings=None, n_files=None, write_ipx=True, overwrite_ipx=True):
    from fire.interfaces.io_utils import filter_files_in_dir
    from fire.interfaces.camera_data_formats import get_ircam_raw_int_nframes_and_shape


    today_str = datetime.now().strftime('%Y-%m-%d')
    date_str = today_str if (date == 'today') else date
    path_in = Path(str(path_in).format(today=today_str, date=date_str))

    if meta is None:
        meta = {}
    if camera_settings is None:
        camera_settings = {}
    meta = copy(meta)
    meta.update(camera_settings)  # copy camera name etc

    files = filter_files_in_dir(path_in, fn_pattern=fn_in, group_keys=fn_in_group_keys)  # , pulse=pulse_whitelist)
    files_filtered = {}

    if n_files is None:
        n_files = len(files)

    print(f'Located {len(files)} raw movie files in folder ""{path_in}":\n{list(files.keys())}"')

    for i, (keys, fn0) in enumerate(reversed(files.items())):
        if pulse_blacklist is not None:
            if keys in make_iterable(pulse_blacklist):
                continue
        if pulse_whitelist is not None:
            if keys not in make_iterable(pulse_whitelist):
                continue

        files_filtered[keys] = fn0

        kws = dict(zip(make_iterable(fn_in_group_keys), make_iterable(keys)))
        meta.update(kws)

        fn_raw_src = (Path(path_in) / fn0).expanduser()
        fn_raw_dest = (Path(path_out.format(**meta)) / fn_raw_out.format(**meta)).expanduser()

        # Copy file from temparary to local structured archive
        io_basic.copy_file(fn_raw_src, fn_raw_dest, mkdir_dest=True)

        nframes, shape = get_ircam_raw_int_nframes_and_shape(fn_raw_src)

        fn_meta_out = fn_meta.format(**meta)
        generate_json_movie_meta_data_file(fn_raw_dest.parent, fn_meta_out, nframes, image_shape=shape,
                                           meta_data_dict=camera_settings)
        if write_ipx:
            # Create ipx file in same directory
            fn_ipx = fn_raw_dest.with_name(fn_ipx_format.format(pulse=keys))
            if overwrite_ipx or (not fn_ipx.is_file()):
                generate_ipx_file_from_ircam_raw_movie(fn_raw_dest, fn_ipx, pulse=keys, plot_check=False)
            # generate_ipx_file_from_ircam_raw(dest, meta_data_dict=camera_settings)

        if len(files_filtered) == n_files:
            logger.info(f'Stopped copying after {n_files} files')
            break
    logger.info(f'Copied raw movie files and generated json meta data for {len(files_filtered)} pulses: '
                f'{list(files_filtered.keys())}')

def copy_raw_files_from_staging_area(date='today', n_files=None, write_ipx=True, overwrite_ipx=True,
                                     path_archive='/home/tfarley/data/movies/diagnostic_pc_transfer/rit/{date}/',
                                     path_out='~/data/movies/mast_u/{pulse}/{camera}/'):
    pulse_whitelist = None
    camera_settings = dict(camera='rit', fps=400, exposure=0.25e-3, lens=25e-3, t_before_pulse=100e-3)

    # fn_in = 'MASTU_LWIR_HL04A-(\d+).RAW'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210128/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210130/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210203/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210209/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210211/'  # NOTE: t_before_pulse is incorrect for shots before 43331

    # fn_in = 'rit_(\d+).RAW'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210215/'

    fn_in = '(\d+).RAW'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210216/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210218/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210224/'

    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210225/'
    # camera_settings = dict(camera='rit', fps=430, exposure=0.1e-3, lens=25e-3, t_before_pulse=100e-3)
    # pulse_whitelist = [43547]

    # camera_settings = dict(camera='rit', fps=430, exposure=0.25e-3, lens=25e-3, t_before_pulse=100e-3)
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210226/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210227/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210228/'

    # camera_settings = dict(camera='rit', fps=400, exposure=0.25e-3, lens=25e-3, t_before_pulse=100e-3)
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210301/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210302/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210309/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210325/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210326/'
    # fn_in = '(\d+).raw'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210329/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210429/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210430/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210504/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210505/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210507/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210510/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210511/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210512/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/Ops_20210513/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/2021-05-18/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/2021-05-19/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/2021-05-20/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/2021-05-21/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/2021-05-25/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/2021-05-26/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/2021-05-27/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-05-28/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-02/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-03/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-04/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-15/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-16/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-17/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-18/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-22/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-23/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-24/'
    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-25/'

    # path_in = '/home/tfarley/ccfepc/T/tfarley/RIT/2021-06-30/'

    camera_settings = dict(camera='rit', fps=400, exposure=0.25e-3, lens=25e-3, t_before_pulse=1e-1)
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-06-29/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-06-30/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-01/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-05/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-06/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-07/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-08/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-09/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-13/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-27/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-28/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-07-29/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-03/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-04/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-11/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-12/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-13/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-18/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-19/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-20/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-24/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-08-26/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-09-01/'
    # path_in = '/home/tfarley/data/movies/diagnostic_pc_transfer/2021-09-08/'

    if path_archive is not None:
        today_str = datetime.now().strftime('%Y-%m-%d')

        if (date == 'today'):
            date_str = today_str
        elif isinstance(date, int):
            date_str = (datetime.today()-timedelta(days=-date)).strftime('%Y-%m-%d')
        else:
            date_str = date
        print(f'Date: {date_str}')
        path_in = Path(str(path_archive).format(today=today_str, date=date_str))

    # TODO: Extract camera settings meta data from spreadsheet

    try:
        organise_ircam_raw_files(path_in=path_in, fn_in=fn_in, path_out=path_out, camera_settings=camera_settings,
                                 pulse_whitelist=pulse_whitelist, n_files=n_files, write_ipx=write_ipx,
                                 overwrite_ipx=overwrite_ipx)
    except OSError as e:
        logger.exception(f'Failed to copy raw IRCAM files from: {path_in}')
    pass


if __name__ == '__main__':
    # copy_raw_files_from_staging_area(write_ipx=True, date=-3)
    # copy_raw_files_from_staging_area(write_ipx=True, date=0)
    copy_raw_files_from_staging_area(write_ipx=True, date='2021-09-30')
    # convert_raw_files_archive_to_ipx(path=Path('~/data/movies/mast_u/44777/rit/').expanduser())

    # path_ats = '~/data/movies/mast_u/rir_ats_files/{date}'

    # convert_ats_files_archive_to_ipx(path_in=path_ats, copy_ats_file=False,
    #                                  fn_ats='0{pulse}.ats',
    #                                  # fn_ats='rir-0{pulse}.ats',
    #                                  # date='today',
    #                                  date='2021-09-30',
    #                                  # pulses=[44677],
    #                                  # date='2021-05-13',
    #                                  # pulses=[43952],  # Calibration movie
    #                                  # pulses=[44980],  # Calibration movie
    #                                  )