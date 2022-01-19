#!/usr/bin/env python

"""


Created: 
"""

import logging
from copy import copy
from typing import Union, Iterable, Sequence, Tuple, Optional, Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from fire.plotting import plot_tools
from fire.plugins.movie_plugins import ipx, uda

logger = logging.getLogger(__name__)
logger.propagate = False

def ipx_write_example():
    pulse = 29852
    path_fn_ipx = f'test_{pulse}.ipx'
    frame_nos, frame_times, movie_data = uda.read_movie_data(pulse, 'rir')
    header_dict = uda.read_movie_meta(pulse, 'rir')
    header_dict['frame_times'] = frame_times
    verbose = True
    ipx.write_ipx_with_mastmovie(path_fn_ipx, movie_data, header_dict, verbose)

def complete_meta_data_dict(meta_data_dict, n_frames=None, image_shape=None, replace=False):
    fps = meta_data_dict['fps']
    t_before_pulse = meta_data_dict['t_before_pulse']  # 1e-1
    period = 1 / fps

    if n_frames is None:
        n_frames = meta_data_dict['n_frames']
    if image_shape is None:
        image_shape = meta_data_dict['image_shape']

    # n_frames = len(frame_data)
    # image_shape = list(frame_data.shape[1:])
    detector_window = [0, 0] + list(image_shape)[::-1]
    frame_numbers = np.arange(n_frames).tolist()

    # Make sure frame frame times are centred around frame at t=0
    # TODO: Apply frame rate correction?
    frame_times = list(np.arange(0, -t_before_pulse, -period)[::-1])
    frame_times = frame_times + list(np.arange(period, (n_frames - len(frame_times) + 1) * period, period))

    t_range = [min(frame_times), max(frame_times)]
    frame_range = [min(frame_numbers), max(frame_numbers)]
    width = image_shape[1]
    height = image_shape[0]

    dict_out = copy(meta_data_dict)
    dict_out.update(dict(n_frames=n_frames, image_shape=image_shape, detector_window=detector_window,
                         width=width, height=height, top=0, left=0, right=width, bottom=height,
                        frame_period=period, lens=25e-3, bit_depth=14, t_range=t_range, frame_range=frame_range,
                                    exposure=0.25e-3,  frame_numbers=frame_numbers, frame_times=frame_times,
                                    t_before_pulse=t_before_pulse))
    if not replace:
        dict_out.update(meta_data_dict)
    return dict_out

def look_up_lwir1_meta_data(shot):
    from fire.interfaces.interfaces import lookup_pulse_row_in_df
    path_fn_lwir1_meta_data = './meta_data_record/Record_of_IRCAM_Velox_81kL_0102A_Operating_Settings-2022_01_17.xlsx'

    df = pd.read_excel(path_fn_lwir1_meta_data, header=4)
    
    meta_data = lookup_pulse_row_in_df(df, shot, allow_overlaping_ranges=False, description=fn, raise_=True)

    return meta_data


def generate_json_meta_data_file_for_ircam_raw(path, fn, n_frames, image_shape, meta_data_dict):
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

    fps = meta_data_dict['fps']
    view = meta_data_dict.get('view', 'HL04_A-tangential')
    t_before_pulse = meta_data_dict['t_before_pulse']  # 1e-1
    period = 1/fps

    # n_frames = len(frame_data)
    # image_shape = list(frame_data.shape[1:])
    detector_window = [0, 0] + list(image_shape)[::-1]
    frame_numbers = np.arange(n_frames).tolist()

    # Make sure frame frame times are centred around frame at t=0. Matters when running at max odd frame rate number?
    # TODO: Check this is necessary? Don't think clock signal eg xpx/clock/lwir-1 does ensure frame at t=0s
    # frame_times = list(safe_arange(0, -t_before_pulse, -period)[::-1])
    # frame_times = frame_times + list(safe_arange(period, (n_frames-len(frame_times))*period, period))
    frame_times = safe_arange(-t_before_pulse, -t_before_pulse+(n_frames*period), period)

    t_range = [min(frame_times), max(frame_times)]
    frame_range = [min(frame_numbers), max(frame_numbers)]

    dict_out = dict(n_frames=n_frames, image_shape=image_shape, detector_window=detector_window, frame_period=period,
                    lens=25e-3, bit_depth=14, t_range=t_range, frame_range=frame_range, exposure=0.25e-3,
                    frame_numbers=frame_numbers, frame_times=frame_times, t_before_pulse=t_before_pulse)
    dict_out.update(meta_data_dict)

    list_out = list(dict_out.items())

    assert len(frame_times) == n_frames

    json_dump(list_out, fn, path, overwrite=True)
    logger.info(f'Wrote meta data file to: {path}/{fn}')


def generate_ipx_file_from_ircam_raw_movie(path_fn_raw, path_fn_ipx, pulse, verbose=True, plot_check=False):
    # from fire.interfaces.camera_data_formats import read_ircam_raw_int16_sequence_file
    from fire.plugins.movie_plugins.raw_movie import read_movie_data, read_movie_meta
    from fire.plugins.movie_plugins.ipx import write_ipx_with_mastmovie
    from fire.plugins.movie_plugins.ipx import read_movie_data_with_mastmovie, read_movie_data_with_pyipx
    from fire.plugins.movie_plugins.ipx import read_movie_meta_with_mastmovie, read_movie_meta_with_pyipx
    from fire.misc import utils
    # from ccfepyutils.mast_data.get_data import get_session_log_data
    # import pyuda
    # client = pyuda.Client()

    # movie_reader = MovieReader(plugin_filter=('raw_movie', 'ats_movie'))
    # frame_numbers, frame_times, frame_data = movie_reader.read_movie_data(pulse=pulse, camera='rir', machine='mast_u')
    # meta_data_dict = movie_reader.read_movie_meta_data(pulse=pulse, camera='rir', machine='mast_u')
    meta_data_dict = read_movie_meta(path_fn_raw)
    frame_numbers, frame_times, frame_data = read_movie_data(path_fn_raw)
    print(f'Read IRCAM raw file {path_fn_raw}')

    # frame_data = frame_data - frame_data[1]  # tmp

    meta_data_dict['shot'] = int(pulse)
    if meta_data_dict['fps'] != 400:  # When fps was set to 430 is was actually still aprox 400
        meta_data_dict['fps'] = 400
        meta_data_dict = complete_meta_data_dict(meta_data_dict, replace=True)  # Update frame times
        # TODO: Get frame times from trigger signal?

    meta_data_dict['frame_times'] = frame_times
    # n_frames, height, width = tuple(frame_data.shape)
    # image_shape = (height, width)
    #
    # pulse = meta_data_dict['shot']
    # # camera = meta_data_dict['camera']
    #
    # meta_data_dict = complete_meta_data_dict(meta_data_dict, n_frames=n_frames, image_shape=image_shape)
    #


    # exec(f'import pyuda; client = pyuda.Client(); date_time = client.get_shot_date_time({pulse})')

    # fill in some dummy fields
    # header = dict(
    #     shot=pulse,
    #     date_time='<placeholder>',
    #     camera='IRCAM_Velox81kL_0102',
    #     view='HL04_A-tangential',
    #     lens='25 mm',
    #     trigger=-np.abs(meta_data_dict['t_before_pulse']),
    #     exposure=int(meta_data_dict['exposure']*1e6),
    #     num_frames=n_frames,
    #     frame_width=width,
    #     frame_height=height,
    #     depth=14,
    # )
    pil_frames = write_ipx_with_mastmovie(path_fn_ipx, frame_data, header_dict=meta_data_dict, verbose=True)

    if plot_check:
        n = 250
        frame_original = frame_data[n]

        frame_numbers_mastmovie, frame_times_mastmovie, data_mastmovie = read_movie_data_with_mastmovie(path_fn_ipx)
        meta_mastmovie = read_movie_meta_with_mastmovie(path_fn_ipx)
        frame_mastmovie = data_mastmovie[n]

        frame_numbers_pyipx, frame_times_pyipx, data_pyipx = read_movie_data_with_pyipx(path_fn_ipx)
        meta_pyipx = read_movie_meta_with_pyipx(path_fn_ipx)
        frame_pyipx = data_pyipx[n]

        for dic in [meta_data_dict, meta_mastmovie, meta_pyipx]:
            for key in ['frame_times', 'shot']:
                if key in dic:
                    dic.pop(key)
        utils.compare_dict(meta_data_dict, meta_mastmovie)
        utils.compare_dict(meta_data_dict, meta_pyipx)

        # print(meta_data_dict)
        # print(meta_mastmovie)

        # plt.ion()
        fig, axes, ax_passed = plot_tools.get_fig_ax(ax=None, ax_grid_dims=(2, 3), sharex=True, sharey=True,
                                                     axes_flatten=True)
        fig.suptitle(f'{pulse}, n={n}')

        ax = axes[0]
        im0 = ax.imshow(frame_original, interpolation='none', origin='upper', cmap='gray')  # , vmin=0, vmax=2**14-1)
        # plt.colorbar(im0)
        ax.set_title(f'Original raw')

        ax = axes[1]
        im1 = ax.imshow(frame_mastmovie, interpolation='none', origin='upper', cmap='gray')  # , vmin=0, vmax=2**14-1)
        # plt.colorbar(im1)
        ax.set_title(f'Mastvideo output')

        ax = axes[2]
        im2 = ax.imshow(frame_pyipx, interpolation='none', origin='upper', cmap='gray')  # , vmin=0, vmax=2**14-1)
        # plt.colorbar(im1)
        ax.set_title(f'pyIpx output')

        ax = axes[3]
        im2 = ax.imshow(frame_original-frame_original, interpolation='none', origin='upper', cmap='gray')
        # plt.colorbar(im1)
        ax.set_title(f'Original-Original')

        ax = axes[4]
        im2 = ax.imshow(frame_original - frame_mastmovie, interpolation='none', origin='upper', cmap='gray')
        # plt.colorbar(im1)
        ax.set_title(f'Original-mastmovie output')
        print('Original - mastmovie', np.max(frame_original-frame_mastmovie), np.mean(frame_original-frame_mastmovie))

        ax = axes[5]
        im2 = ax.imshow(frame_original-frame_pyipx, interpolation='none', origin='upper', cmap='gray')
        # plt.colorbar(im1)
        ax.set_title(f'Original-pyIpx output')
        print('Original - pyIpx', np.max(frame_original-frame_pyipx), np.mean(frame_original-frame_pyipx))


        plt.tight_layout()
        plt.show()

        pil_frames[n].show(title=f'PIL native show {pulse}, {n}')
        pass

if __name__ == '__main__':
    ipx_write_example()
    pass