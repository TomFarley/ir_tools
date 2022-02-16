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
from fire.plugins.movie_plugins import ats_movie
from fire.interfaces.camera_data_formats import get_ircam_raw_int_nframes_and_shape
from fire.plotting import plot_tools
from ir_tools.data_formats import ircam_raw_movies_to_ipx, flir_ats_movie_to_ipx
from ir_tools.data_formats import update_spreadsheet

logger = logging.getLogger(__name__)

path_pre_ipx_archive = Path('/projects/SOL/Data/Cameras/IR')
path_ipx_archive = Path('/projects/SOL/Data/Cameras/IR/ipx')

def convert_ircam_raw_files_archive_to_ipx(shots=None, skip_existing=True, n_convert=None):
    tag = 'rit'
    path_raw_root = path_pre_ipx_archive / tag.upper()  #  Path('~/data/movies/mast_u/').expanduser()
    path_fn_ss = './meta_data_record/Record_of_IRCAM_Velox_81kL_0102A_Operating_Settings.xlsx'
    col_names = ['pulse', 'date', 'exposure', 'fps', 'frame_period', 'n_frames', 'duration', 'trigger',
                     'detector_window', 'lens', 'view', 'filter', 'issues', 'comments']

    shots_converted = []
    shots_ss_modified = []
    shots_skipped = []
    shots_failed = []
    fns_failed = []

    date_dirs = sorted(path_raw_root.glob("*/"))

    for date_dir in date_dirs:

        path_fns_raw = sorted(date_dir.glob('*.raw'))
        path_fns_raw += sorted((date_dir.glob('*.RAW')))
        # print(path_fns_raw)
        logger.info(f'converted={len(shots_converted)}, skipped={len(shots_skipped)}, failed={len(shots_failed)}')
        logger.info(f'"{date_dir.parent}" date_dir contains {len(path_fns_raw)} raw/RAW files: {date_dir}')

        for path_fn_raw in path_fns_raw:
            try:
                m = re.search('(\d{5})\.', str(path_fn_raw.name))
                if m is not None:
                    shot = int(m.groups()[0])
                else:
                    logger.warning(f'Failed to extract pulse number from raw file: {path_fn_raw}')
                    fns_failed.append(path_fn_raw)
                    continue

                if (shots is not None) and (shot not in shots):
                    continue

                path_fn_ipx = path_ipx_archive / f'0{str(shot)[:2]}/{shot}' / f'{tag}0{shot}.ipx'
                if skip_existing and path_fn_ipx.is_file():
                    shots_skipped.append(shot)
                    logger.info(f'Skipped shot "{shot}" with existing ipx file')
                    continue

                fn_meta = f'{tag}0{shot}_meta.json'
                path_fn_meta = path_fn_raw.parent / fn_meta

                meta_data_dict, nframes_ss, imageshape_ss = look_up_ir_meta_data_from_spreadsheet(path_fn_ss,
                                                                                                shot, diag_tag_raw=tag,
                                                                                                col_names=col_names)
                meta_data_dict['camera'] = 'IRCAM Velox_81kL_0102A18CH_FAST'  # camera used in first campaign

                n_frames_file, image_shape_file = get_ircam_raw_int_nframes_and_shape(path_fn_raw, shape=imageshape_ss)

                ss_correct = True
                if (nframes_ss != n_frames_file) or (np.any(imageshape_ss != image_shape_file)):
                    message = (f'Meta data for "{shot}" from spreadsheet appears to be incorrect:'
                                f'{nframes_ss} (ss) != {n_frames_file} (file) or {imageshape_ss} != {image_shape_file}')
                    logger.warning(message)
                    ss_correct = False

                    # shots_failed.append(shot)
                    # fns_failed.append(path_fn_raw)
                    # continue
                    # raise ValueError(message)

                meta_data_json = generate_json_movie_meta_data_file(path_fn_meta.parent, fn=fn_meta,
                                    n_frames=n_frames_file, image_shape=image_shape_file, meta_data_dict=meta_data_dict)
                if not ss_correct:
                    shots_ss_modified.append(shot)
                    update_spreadsheet.modify_row_in_spreadsheet(path_fn_ss, row_dict=meta_data_json,
                                                                 col_names=col_names)

                io_basic.mkdir(path_fn_ipx, depth=3)

                ircam_raw_movies_to_ipx.generate_ipx_file_from_ircam_raw_movie(path_fn_raw=path_fn_raw,
                                            path_fn_ipx=path_fn_ipx, path_fn_meta=path_fn_meta,
                                            pulse=shot, verbose=True, plot_check=False)
                shots_converted.append(shot)

                if (n_convert is not None) and (len(shots_converted) >= n_convert):
                    logger.info(f'Converted required number of files: {n_convert}')
                    break
            except Exception as e:
                logger.exception(e)
                shots_failed.append(shot)
                fns_failed.append(path_fn_raw)
        if (n_convert is not None) and (len(shots_converted) >= n_convert):
            break

    shots_with_raw_data = np.concatenate([shots_converted, shots_skipped, shots_failed])
    if shots is None:
        shots_in_range = np.arange(np.min(shots_with_raw_data), np.max(shots_with_raw_data)+1, dtype=int)
    else:
        shots_in_range = np.arange(np.min(shots), np.max(shots)+1, dtype=int)
    shots_missing_data = np.array(list(set(shots_in_range) - set(shots_with_raw_data)))

    logger.info(f'Skipped {len(shots_skipped)} to ipx: {shots_skipped}')
    logger.info(f'Converted {len(shots_converted)} to ipx: {shots_converted}')
    logger.info(f'Modified spreadsheet {len(shots_ss_modified)} to ipx: {shots_ss_modified}')
    logger.info(f'Failed {len(shots_failed)}: {shots_failed}')
    logger.info(f'No data {len(shots_missing_data)}: {shots_missing_data}')

    logger.info(f'Total {len(shots_converted)+len(shots_skipped)+len(shots_missing_data)+len(shots_failed)} == range {len(shots_in_range)}')
    if shots is not None:
        logger.info(f'Requested: {len(shots)}, n_convert: {n_convert}')

    logger.info(f'Files failed: {fns_failed}')

    fig, ax = plt.subplots()
    ax.plot(shots_converted, np.ones_like(shots_converted), ls='', marker='o', color='g', label='converted to ipx')
    ax.plot(shots_skipped, 0.95*np.ones_like(shots_skipped), ls='', marker='o', color='b', label='existing ipx')
    ax.plot(shots_failed, 0.05*np.ones_like(shots_failed), ls='', marker='x', color='r', label='failed')
    ax.plot(shots_missing_data, 0.0*np.ones_like(shots_missing_data), ls='', marker='x', color='orange', label='missing raw')

    ax.grid()
    plot_tools.legend(ax)
    plt.show()

def convert_flir_ats_files_archive_to_ipx(shots=None, skip_existing=True, n_convert=None, plot_check=False):
    tag = 'rir'
    camera = 'FLIR_SC7500_6580045'
    path_fn_ss = './meta_data_record/Record_of_MWIR1_FLIR_SC7500_6580045_Operating_Settings.xlsx'
    col_names = ['shot', 'date', 'exposure', 'fps', 'frame_period', 'n_frames', 'duration', 'trigger',
                     'detector_window', 'lens', 'view', 'filter', 'issues', 'comments']
    ext = 'ats'

    path_raw_root = path_pre_ipx_archive / tag.upper()  #  Path('~/data/movies/mast_u/').expanduser()

    shots_converted = []
    shots_ss_modified = []
    shots_skipped = []
    shots_failed = []
    fns_failed = []

    date_dirs = sorted(path_raw_root.glob("*/"))

    for date_dir in date_dirs:

        path_fns_ats = sorted(date_dir.glob(f'*.{ext}'))
        path_fns_ats += sorted((date_dir.glob(f'*.{ext.upper()}')))
        # print(path_fns_raw)
        logger.info(f'converted={len(shots_converted)}, skipped={len(shots_skipped)}, failed={len(shots_failed)}')
        logger.info(f'"{date_dir.parent}" date_dir contains {len(path_fns_ats)} {ext}/{ext.upper()} files: {date_dir}')

        for path_fn_ats in path_fns_ats:
            try:
                m = re.search('(\d{5})\.', str(path_fn_ats.name))
                if m is not None:
                    shot = int(m.groups()[0])
                else:
                    logger.warning(f'Failed to extract pulse number from ats file: {path_fn_ats}')
                    fns_failed.append(path_fn_ats)
                    continue

                if (shots is not None) and (shot not in shots):
                    continue

                path_fn_ipx = path_ipx_archive / f'0{str(shot)[:2]}/{shot}' / f'{tag}0{shot}.ipx'
                if skip_existing and path_fn_ipx.is_file():
                    shots_skipped.append(shot)
                    logger.info(f'Skipped shot "{shot}" with existing ipx file')
                    continue

                fn_meta = f'{tag}0{shot}_meta.json'
                path_fn_meta = path_fn_ats.parent / fn_meta

                meta_data_dict_ss, nframes_ss, imageshape_ss = look_up_ir_meta_data_from_spreadsheet(path_fn_ss, shot,
                                                                                diag_tag_raw=tag, col_names=col_names)
                meta_data_dict_ss['camera'] = camera  # camera used in first campaign
                meta_data_dict_ss['n_frames'] = nframes_ss
                meta_data_dict_ss['image_shape'] = imageshape_ss

                meta_data_dict_file = ats_movie.read_movie_meta(path_fn_ats, raise_on_missing_meta=False)

                n_frames_file = meta_data_dict_file['n_frames']
                image_shape_file = meta_data_dict_file['image_shape']
                exposure_file = meta_data_dict_file['exposure']

                ss_checks = {'n_frames': 'n_frames', 'exposure': 'exposure', 'image_shape': 'image_shape'}
                ss_correct = True
                for key_ss, key_file in ss_checks.items():
                    if np.any(meta_data_dict_ss[key_ss] != meta_data_dict_file[key_file]):
                        logger.warning(f'SS value error for "{shot}", "{key_ss}": '
                                       f'{meta_data_dict_ss[key_ss]} != {meta_data_dict_file[key_file]} (file) ({date_dir.name})')
                        ss_correct = False
                # if not ss_correct:
                #     shots_failed.append(shot)
                #     fns_failed.append(path_fn_ats)
                #     continue

                meta_data_dict = {**meta_data_dict_ss, **meta_data_dict_file}

                meta_data_json = generate_json_movie_meta_data_file(path_fn_meta.parent, fn=fn_meta,
                                                   n_frames=n_frames_file, image_shape=image_shape_file,
                                                   meta_data_dict=meta_data_dict)

                ss_checks = {'fps': 'fps'}
                # ss_correct = True
                for key_ss, key_file in ss_checks.items():
                    if np.any(meta_data_dict_ss[key_ss] != meta_data_json[key_file]):
                        logger.warning(f'SS value error for "{shot}", "{key_ss}": '
                                       f'{meta_data_dict_ss[key_ss]} != {meta_data_json[key_file]} (file)')
                        ss_correct = False
                if not ss_correct:
                    shots_ss_modified.append(shot)
                    update_spreadsheet.modify_row_in_spreadsheet(path_fn_ss, row_dict=meta_data_json,
                                                                 col_names=col_names)
                    # shots_failed.append(shot)
                    # fns_failed.append(path_fn_ats)
                    # continue

                io_basic.mkdir(path_fn_ipx, depth=3)

                flir_ats_movie_to_ipx.generate_ipx_file_from_flir_ats_movie(path_fn_ats=path_fn_ats, path_fn_ipx=path_fn_ipx,
                                                                        pulse=shot, verbose=True, plot_check=plot_check)

                shots_converted.append(shot)

                if (n_convert is not None) and (len(shots_converted) >= n_convert):
                    logger.info(f'Converted required number of files: {n_convert}')
                    break
            except Exception as e:
                logger.exception(e)
                shots_failed.append(shot)
                fns_failed.append(path_fn_ats)
        if (n_convert is not None) and (len(shots_converted) >= n_convert):
            break

    shots_with_raw_data = np.concatenate([shots_converted, shots_skipped, shots_failed])
    if shots is None:
        shots_in_range = np.arange(np.min(shots_with_raw_data), np.max(shots_with_raw_data)+1, dtype=int)
    else:
        shots_in_range = np.arange(np.min(shots), np.max(shots)+1, dtype=int)
    shots_missing_data = np.array(list(set(shots_in_range) - set(shots_with_raw_data)))

    logger.info(f'Skipped {len(shots_skipped)} to ipx: {shots_skipped}')
    logger.info(f'Converted {len(shots_converted)} to ipx: {shots_converted}')
    logger.info(f'Modified spreadsheet {len(shots_ss_modified)} to ipx: {shots_ss_modified}')
    logger.info(f'Failed {len(shots_failed)}: {shots_failed}')
    logger.info(f'No data {len(shots_missing_data)}: {shots_missing_data}')

    logger.info(f'Total {len(shots_converted)+len(shots_skipped)+len(shots_missing_data)+len(shots_failed)} == range {len(shots_in_range)}')
    if shots is not None:
        logger.info(f'Requested: {len(shots)}, n_convert: {n_convert}')

    logger.info(f'Files failed: {fns_failed}')

    fig, ax = plt.subplots()
    ax.plot(shots_converted, np.ones_like(shots_converted), ls='', marker='o', color='g', label='converted to ipx')
    ax.plot(shots_skipped, 0.95*np.ones_like(shots_skipped), ls='', marker='o', color='b', label='existing ipx')
    ax.plot(shots_failed, 0.05*np.ones_like(shots_failed), ls='', marker='x', color='r', label='failed')
    ax.plot(shots_missing_data, 0.0*np.ones_like(shots_missing_data), ls='', marker='x', color='orange', label='missing raw')

    ax.grid()
    plot_tools.legend(ax)
    plt.show()

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

def organise_ircam_datac_ipx_files():
    ext = 'ipx'
    path_unsorted = path_pre_ipx_archive / 'RIT' / 'ipx_files'
    tag = 'rit'

    path_fns_unsorted = sorted(path_unsorted.glob(f'*.{ext}'))
    # print(path_fns_raw)
    logger.info(f'"{path_unsorted}" contains {len(path_fns_unsorted)} {ext} files: {path_fns_unsorted}')

    success = []
    failed = []

    for path_fn_ipx_unsorted in path_fns_unsorted:
        try:
            m = re.search('(\d{5})\.', str(path_fn_ipx_unsorted.name))
            if m is not None:
                shot = int(m.groups()[0])
            else:
                logger.warning(f'Failed to extract pulse number from ats file: {path_fn_ipx_unsorted}')
                failed.append(shot)
                continue

        except Exception as e:
            failed.append(shot)
            continue

        path_fn_ipx_new = path_ipx_archive / f'0{str(shot)[:2]}/{shot}' / f'{tag}0{shot}.ipx'

        io_basic.copy_file(path_fn_ipx_unsorted, path_fn_ipx_new, verbose=True, mkdir_dest=True)
        success.append(shot)

    logger.info(f'Successes: {len(success)}, Failed: {len(failed)}')
    logger.info(f'Successes: {success}')
    logger.info(f'Failed: {failed}')


def convert_ats_files_archive_to_ipx(pulses=None, path_in=None, exp_date=None, copy_ats_file=False, fn_ats='0{pulse}.ats',
                                     fn_meta='/home/tfarley/data/movies/mast_u/rir_ats_files/rir_meta.json',
                                     n_files=None):
    from fire.interfaces.interfaces import locate_file
    from fire.interfaces.io_utils import filter_files, filter_files_in_dir
    path_root = Path('~/data/movies/mast_u/').expanduser()

    success, failed = [], []

    if (exp_date is None) or (exp_date == 'today'):
        exp_date = datetime.now().strftime('%Y-%m-%d')

    if path_in is not None:
        path_in = Path(str(path_in).format(date=exp_date)).expanduser()
    else:
        path_in = path_root / exp_date

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


def generate_json_movie_meta_data_file(path, fn, n_frames, image_shape, meta_data_dict):
    """
    See movie_meta_required_fields in plugins_movie.py, line ~260:
      ['n_frames', 'frame_range', 't_range', 'fps', 'lens', 'exposure', 'bit_depth', 'image_shape', 'detector_window']

    Args:
        path:
        fn:
        frame_data:
        meta_data_dict:

    Returns:

    """
    from fire.interfaces.io_basic import json_dump
    from fire.misc.utils import safe_arange
    from fire.plugins.machine_plugins.mast_u import get_shot_date_time, get_shot_date, get_camera_external_clock_info

    shot = int(re.match('.*(\d{5}).*', fn).groups()[0])

    camera = meta_data_dict['camera']  # , 'IRCAM Velox_81kL_0102A18CH_FAST')
    if camera == 'IRCAM Velox_81kL_0102A18CH_FAST':
        diag_tag_raw = 'rit'
    elif camera == 'FLIR_SC7500_6580045':
        diag_tag_raw = 'rir'
    else:
        raise ValueError(camera)

    fps = meta_data_dict['fps']
    exposure = meta_data_dict['exposure']  # 0.25e-3
    lens = meta_data_dict.get('lens', '25mm')  #
    view = meta_data_dict['view']  # , 'HL04_A-tangential')
    t_before_pulse = meta_data_dict.get('t_before_pulse', 1e-1)  # 1e-1
    period = meta_data_dict.get('frame_period', 1/fps)
    orient = meta_data_dict.get('orient', 90)  # Rotation to apply to data to get correct orientation
    filter = meta_data_dict['filter']  # nd filter etc
    taps = meta_data_dict['taps']  # number of digitisers (2 on FLIR)
    frame_numbers = meta_data_dict.get('frame_numbers', np.arange(n_frames)).tolist()
    frame_times = meta_data_dict.get('frame_times', None)

    date_time = get_shot_date_time(shot)
    date = get_shot_date(shot)

    # n_frames = len(frame_data)
    image_shape = image_shape.tolist()
    detector_window = meta_data_dict.get('detector_window', np.array([0, 0] + list(image_shape)[::-1])).tolist()

    # Make sure frame frame times are centred around frame at t=0. Matters when running at max odd frame rate number?
    # TODO: Check this is necessary? Don't think clock signal eg xpx/clock/lwir-1 does ensure frame at t=0s
    # frame_times = list(safe_arange(0, -t_before_pulse, -period)[::-1])
    # frame_times = frame_times + list(safe_arange(period, (n_frames-len(frame_times))*period, period))
    if (frame_times is None) or np.all(np.isnan(frame_times)):
        if n_frames > 1:
            if np.isnan(period):
                period = 1/fps
            frame_times = safe_arange(-t_before_pulse, -t_before_pulse+((n_frames-1)*period), period).tolist()
        else:
            frame_times = [-t_before_pulse]
    # TODO: Get frame times from trigger signal?

    clock_info = get_camera_external_clock_info(camera=diag_tag_raw, pulse=shot, n_frames=n_frames,
                                    frame_numbers=frame_numbers, dropped_frames=meta_data_dict.get('dropped_frames'))
    if clock_info is not None:
        frame_times = np.array(clock_info['clock_frame_times'])[:n_frames].tolist()
        if not np.isclose(fps, clock_info['clock_frequency']):
            message = (f'fps, clock_frequency: {fps}, {clock_info["clock_frequency"]}')
            logger.warning(message)
            fps = float(clock_info['clock_frequency'])
    else:
        logger.warning(f'No clock info for shot {shot}')

    if isinstance(frame_times, np.ndarray):
        frame_times = frame_times.tolist()

    t_range = [min(frame_times), max(frame_times)]
    frame_range = [min(frame_numbers), max(frame_numbers)]

    # Calcam order conventions - (Left,Top,Width,Height), 0-indexed
    left, top, width, height = detector_window
    left += 1
    top += 1
    # IPX index conventions - left, top etc start are indexed from 1 (0 is missing data)
    bottom, right = top+height, left+width
    left = meta_data_dict.get('left', left)
    top = meta_data_dict.get('top', top)
    bottom = meta_data_dict.get('bottom', bottom)
    right = meta_data_dict.get('right', right)

    dict_out = dict(# IPX1 fields:
                    date_time=date_time, shot=shot, trigger=-t_before_pulse, lens=lens, filter=filter, view=view,
                    numFrames=n_frames, camera=camera, width=width, height=height, depth=14, orient=orient, taps=taps,
                    color=0, hBin=0, vBin=0, left=left, top=top, bottom=bottom, right=right, exposure=exposure,
                    # Additional fields/alternative names:
                    diag_tag_raw=diag_tag_raw, n_frames=n_frames, fps=fps, image_shape=image_shape, date=date,
                    detector_window=detector_window, frame_period=period, bit_depth=14,
                    t_range=t_range, frame_range=frame_range,
                    frame_numbers=frame_numbers, frame_times=frame_times, t_before_pulse=t_before_pulse
                    )
    # dict_out.update(meta_data_dict)

    list_out = list(dict_out.items())

    if len(frame_times) != n_frames:
        raise ValueError(f'{shot}: {len(frame_times)} != {n_frames}')
    if np.any(np.array(image_shape[::-1]) != np.array(detector_window[2:])):
        raise ValueError(f'{shot}: Shape and detector window dont match')

    json_dump(list_out, fn, path, overwrite=True)
    logger.info(f'Wrote meta data file to: {path}/{fn}')
    return dict_out

def look_up_ir_meta_data_from_spreadsheet(path_fn_meta_data_ss, shot, diag_tag_raw='rit', col_names=None):
    from fire.interfaces.interfaces import lookup_pulse_row_in_df
    from fire.misc.utils import list_repr_to_list

    if col_names is None:
        col_names = ['shot', 'date', 'exposure', 'fps', 'frame_period', 'n_frames', 'duration', 'trigger',
                     'detector_window', 'lens', 'view', 'filter', 'issues', 'comments']

    try:
        df = pd.read_excel(path_fn_meta_data_ss, header=4,  # index_col='pulse',
                           names=col_names, dtype={'shot': int, 'n_frames': int})
    except Exception as e:
        raise e

    meta_data = lookup_pulse_row_in_df(df, shot, allow_overlaping_ranges=False, description=path_fn_meta_data_ss,
                                       require_pulse_end=False, pulse_name=col_names[0], raise_=True)

    # Convert units and types
    meta_data['t_before_pulse'] = np.abs(meta_data['trigger'])  # s
    meta_data['exposure'] = int(meta_data['exposure'] * 1e0)  # keep in us (IPX convention)
    meta_data['date'] = str(meta_data['date'])
    meta_data['frame_period'] = meta_data['frame_period'] * 1e-6  # convert us to seconds
    # meta_data['lens'] = f'{meta_data["lens"]}mm'  # convert mm to string (Past MAST IR IPX convention)
    # TODO: Add assertion checks of magnitude of values ie correct units

    # Spreadsheet has detector window formatted as used to set up camera
    top, left, height, width = list_repr_to_list(meta_data['detector_window'])
    # Switch to combination of:
    # Calcam order conventions - change order to: (Left,Top,Width,Height)
    # IPX index conventions - left and top start are indexed from 1 (0 is missing data)
    meta_data['detector_window'] = np.array([left, top, width, height], dtype=int)
    meta_data['left'] = left + 1
    meta_data['top'] = top + 1
    meta_data['right'] = left + width + 1
    meta_data['bottom'] = top + height + 1

    image_shape = np.array([height, width])  # Note image_shape is reversed wrt order in detector_window

    if meta_data['view'] == 'HL04_A-tangential_1':
        meta_data['orient'] = 90  # Rotation to apply to data to get correct orientation
    elif meta_data['view'] == 'HL04_B-radial_1':
        meta_data['orient'] = 270  # Rotation to apply to data to get correct orientation

    if diag_tag_raw == 'rit':
        meta_data['taps'] = 1
    elif diag_tag_raw == 'rir':
        meta_data['taps'] = 2

    meta_data = meta_data.to_dict()

    n_frames = meta_data.pop('n_frames')

    return meta_data, n_frames, image_shape

def add_shot_to_meta_data_spreadsheet(shot, diag_tag_raw='rit'):

    return


if __name__ == '__main__':
    # start = 43123
    # start = 44793
    # start = 45000
    # n = 500
    # shots = np.arange(start, start+n)
    shots_rit_failed = [43360, 43656, 43683, 43743, 43878, 44041, 44073, 44073, 44577, 44625, 44625, 44758, 44869, 44906, 44923, 44980, 45071, 45085, 45200, 45401]
    shots_rir_failed = [44009, 44041, 44047, 44054, 44203, 44234, 44258, 44258, 44258, 44258, 44304, 44258, 44304, 44775, 44832, 44851, 44906, 44923, 44923, 44924, 44958, 44960, 44961, 44962, 44963, 44964, 44965, 44966, 44967, 44968, 44969, 44970, 44971, 44972, 44973, 44974, 44975, 44976, 44977, 44978, 44979, 44980, 44981, 44982, 44983, 44984, 44985, 44986, 44987, 44988, 44989, 44990, 44991, 44992, 44993, 44994, 44995, 44996, 44997, 44998, 45085, 45091, 45092, 45093, 45098, 45119, 45137, 45138, 45139, 45140, 45141, 45142, 45143, 45144, 45145, 45146, 45149, 45150, 45151, 45152, 45153, 45154, 45156, 45157, 45161, 45162, 45163, 45164, 45165, 45166, 45167, 45168, 45169, 45170, 45171, 45172, 45173, 45174, 45175, 45176, 45177, 45178, 45179, 45180, 45181, 45182, 45183, 45184, 45211, 45212, 45213, 45214, 45215, 45216, 45218, 45219, 45220, 45221, 45224, 45225, 45226, 45227, 45228, 45229, 45231, 45233, 45234, 45235, 45236, 45237, 45238, 45239, 45240, 45241, 45242, 45243, 45244, 45245, 45246, 45247, 45248, 45251, 45252, 45253, 45254, 45255, 45256, 45257, 45258, 45259, 45260, 45261, 45262, 45264, 45265, 45266, 45267, 45268, 45270, 45271, 45272, 45274, 45275, 45276, 45277, 45278, 45279, 45280, 45281, 45282, 45283, 45284, 45285, 45286, 45287, 45288, 45289, 45290, 45291, 45292, 45293, 45294, 45295, 45296, 45297, 45298, 45299, 45300, 45301, 45302, 45303, 45304, 45305, 45306, 45309, 45310, 45311, 45312, 45313, 45314, 45315, 45316, 45317, 45318, 45319, 45320, 45321, 45322, 45323, 45325, 45326, 45327, 45328, 45329, 45330, 45331, 45332, 45333, 45334, 45335, 45336, 45338, 45339, 45340, 45341, 45344, 45345, 45346, 45347, 45348, 45349, 45350, 45351, 45352, 45353, 45354, 45356, 45357, 45358, 45360, 45361, 45362, 45363, 45364, 45365, 45366, 45367, 45368, 45370, 45371, 45372, 45373, 45374, 45375, 45376, 45377, 45378, 45380, 45381, 45382, 45383, 45386, 45387, 45388, 45390, 45391, 45392, 45393, 45395, 45396, 45397, 45398, 45399, 45400, 45401, 45402, 45403, 45403, 45405, 45406, 45407, 45408, 45409, 45411, 45414, 45415, 45416, 45417, 45418, 45419, 45469, 45472]
    # shots = [45419]
    shots = None
    # shots = shots_rit_failed
    # shots = shots_rir_failed
    # convert_ircam_raw_files_archive_to_ipx(shots=shots, skip_existing=True, n_convert=None)
    # convert_flir_ats_files_archive_to_ipx(shots=shots, skip_existing=True, n_convert=None, plot_check=False)

    organise_ircam_datac_ipx_files()
    pass
