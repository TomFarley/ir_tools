#!/usr/bin/env python

"""


Created: 
"""

import logging

from matplotlib import pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

path_ats = '~/data/movies/diagnostic_pc_transfer/rir/{date}'


def generate_ipx_file_from_flir_ats_movie(path_fn_ats, path_fn_ipx, pulse, verbose=True, plot_check=True):
    # from fire.interfaces.camera_data_formats import read_ircam_raw_int16_sequence_file
    from fire.plugins.movie_plugins.ats_movie import read_movie_data, read_movie_meta
    from fire.plugins.movie_plugins.ipx import write_ipx_with_mastmovie
    from fire.plugins.movie_plugins.ipx import read_movie_data as read_movie_data_ipx
    from fire.plugins.movie_plugins.ipx import read_movie_meta as read_movie_meta_ipx

    frame_numbers, frame_times, frame_data = read_movie_data(path_fn_ats)
    meta_data_dict = read_movie_meta(path_fn_ats)
    print(f'Read FLIR ats file {path_fn_ats}')

    # frame_data = frame_data - frame_data[1]  # tmp

    meta_data_dict['shot'] = int(pulse)

    # TODO: Compare to frame times from trigger signal?

    meta_data_dict['frame_times'] = frame_times

    pil_frames = write_ipx_with_mastmovie(path_fn_ipx, frame_data, header_dict=meta_data_dict,
                                          apply_nuc=False, create_path=True, verbose=True)

    if plot_check:
        frame_numbers_out, frame_times_out, data_out = read_movie_data_ipx(path_fn_ipx)
        n = int(np.mean(frame_numbers_out))
        meta_new = read_movie_meta_ipx(path_fn_ipx)
        frame_new = data_out[n]
        frame_original = frame_data[n]

        meta_data_dict.pop('frame_times');
        meta_data_dict.pop('shot');

        print(meta_data_dict)
        print(meta_new)

        plt.ion()
        fig, (ax0, ax1) = plt.subplots(1, 2, sharex=True, sharey=True)
        fig.suptitle(f'{pulse}, n={n}')
        im0 = ax0.imshow(frame_original, interpolation='none', origin='upper', cmap='gray')  # , vmin=0, vmax=2**14-1)
        # plt.colorbar(im0)
        ax0.set_title(f'Original raw')
        im1 = ax1.imshow(frame_new, interpolation='none', origin='upper', cmap='gray')  # , vmin=0, vmax=2**14-1)
        # plt.colorbar(im1)
        ax1.set_title(f'Mastvideo output')
        plt.tight_layout()
        plt.show()

        pil_frames[n].show(title=f'PIL native show {pulse}, {n}')
        pass


if __name__ == '__main__':
    pass