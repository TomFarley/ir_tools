#!/usr/bin/env python

"""


Created: 
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from fire.plotting import plot_tools

logger = logging.getLogger(__name__)

def plot_wireframe():
    NotImplementedError()

def annimate_uda_movie():
    NotImplementedError()

def annimate_ipx_movie(path_fn_ipx):
    from fire.plugins.movie_plugins import ipx
    frame_numbers, frame_times_all, frame_data = ipx.read_movie_data(path_fn_ipx)

    annimate_movie_data(frame_data, frame_times_all, frame_numbers)

def annimate_raw_movie(path_fn_raw):
    from fire.plugins.movie_plugins import raw_movie
    frame_numbers, frame_times_all, frame_data = raw_movie.read_movie_data(path_fn_raw)

    annimate_movie_data(frame_data, frame_times_all, frame_numbers)

def annimate_movie_data(frame_data, frame_times=None, frame_numbers=None, ax=None, duration=None, interval=None,
                       frame_label='', cbar_label=None, label_values=None,
                       cmap='viridis', axes_off=True, fig_kwargs=None,
                       n_start=None, n_end=None, nth_frame=1, cbar_range=None, save_kwargs=None, save_path_fn=None,
                       show=True):
    import matplotlib.animation as anim
    from matplotlib.animation import FuncAnimation
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    # nframes_animate = int((n_end - n_start) / nth_frame)
    # frame_nos = np.arange(n_start, n_end + 1, nth_frame, dtype=int)

    if frame_numbers is None:
        frame_numbers = np.arange(len(frame_data))

    fig, ax, ax_passed = plot_tools.get_fig_ax(ax=ax, **fig_kwargs)

    img_data = frame_data[0]
    img = ax.imshow(img_data, cmap=cmap)

    if cbar_range is not None:
        vmin, vmax = np.percentile(frame_data, cbar_range[0]), np.percentile(frame_data, cbar_range[1])
        if cbar_range[1] != 100 and cbar_range[0] != 0:
            extend = 'both'
        elif cbar_range[1] != 100 and cbar_range[0] == 0:
            extend = 'max'
        elif cbar_range[1] == 100 and cbar_range[0] != 0:
            extend = 'min'
        else:
            extend = 'neither'
    else:
        vmin, vmax = None, None
        extend = 'neither'

    div = make_axes_locatable(ax)
    ax_cbar = div.append_axes('right', '5%', '5%')
    cbar = fig.colorbar(img, cax=ax_cbar, extend=extend, label=cbar_label)
    # tx = ax.set_title(f'Frame 0/{nframes_animate-1}')

    frame_label_i = frame_label.format(**{k: v[n_start] for k, v in label_values.items()})
    text_artist = plot_tools.annotate_axis(ax, frame_label_i, loc='top_left', box=False, color='white')

    if axes_off:
        ax.set_axis_off()

    def update(frame_no, vmin, vmax):
        # xdata.append(frame)
        # ydata.append(np.sin(frame))
        # ln.set_data(xdata, ydata)
        frame = frame_data[frame_no]
        if vmin is None:
            vmax = np.max(frame)
        if vmax is None:
            vmin = np.min(frame)

        img.set_data(frame)
        img.set_clim(vmin, vmax)

        # levels = np.linspace(vmin, vmax, 200, endpoint=True)
        # cf = ax.contourf(frame, vmax=vmax, vmin=vmin, levels=levels)
        # ax_cbar.cla()
        # fig.colorbar(img, cax=ax_cbar)
        frame_label_i = frame_label.format(**{k: v[frame_no] for k, v in label_values.items()})
        text_artist.set_text(frame_label_i)
        # return img, cbar, tx
        # return ln,

    anim = FuncAnimation(fig, update, frames=frame_numbers, fargs=(vmin, vmax),  # np.linspace(0, 2 * np.pi, 128),
                        interval=interval,
                        # init_func=init,
                        blit=False)

if __name__ == '__main__':
    # fn = '/projects/SOL/Data/Cameras/IR/RIT/2021-08-24/None.RAW'
    fn = '/projects/SOL/Data/Cameras/IR/RIT/2021-08-24/44793.RAW'
    annimate_raw_movie(fn)
    pass