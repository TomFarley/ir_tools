#!/usr/bin/env python

"""


Created: 
"""

import logging
from typing import Union, Iterable, Tuple, Optional
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from ccfepyutils.mpl_tools import annotate_axis, get_fig_ax, arrowplot, save_fig
from matplotlib import patches

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

surface_radii = {'R_wall': 2.0,
        'R_HL04': 2.1333,
        'R_T1': 0.333,
        'R_T4': 1.081,
        'R_T5': 1.379,
        'R_T5_top': 1.746,
        'n_sectors': 12,
                 }

camera_views = {'HL04_A-c': {  # clockwise
               'pupil': {'x': 2.019, 'y': -0.356, 'z': -1.55},
               'view': {'x': -0.707, 'y': -0.707, 'z': -2.0},
               'color': 'red',
                },
            'HL04_A-ac': {  # anti-clockwise
               'pupil': {'x': 2.019, 'y': -0.356, 'z': -1.55},
               'view': {'x': -0.423, 'y': 0.906, 'z': -2.0},
               'color': 'green',
                },
            'HL04_LWIR_view_test_09-19_v2.ccc': {  # anti-clockwise
               'pupil': {'x': 2.111, 'y': -0.753, 'z': -1.531},
               'view': {'x': 1.56, 'y': -0.178, 'z': -1.605},
               'color': 'orange',
                },
            'HU04_LWIR_view_mirrored': {  # anti-clockwise
               'pupil': {'x': 2.205, 'y': -0.403, 'z': 1.531},
               'view': {'x': 1.440, 'y': -0.626, 'z': 1.605},
               'color': 'blue',
                },
            'HL04_B_MWIR_view_test_09-19_v1.ccc': {  # radial
                'pupil': {'x': 2.226, 'y': -0.483, 'z': -1.530},
                'view': {'x': 1.254, 'y': -0.282, 'z': -1.652},
                'color': 'yellow',
                },
            'HU04_A_MWIR_view_mirrored': {  # radial
                'pupil': {'x': 2.169, 'y': -0.695, 'z': 1.53},
                'view': {'x': 1.227, 'y': -0.383, 'z': 1.652},
                'color': 'purple',
                },

}


def plot_mast_top_down(ax=None):
    fig, ax = get_fig_ax(ax)

    r_wall = surface_radii['R_wall']
    n_sectors = surface_radii['n_sectors']

    # Plot vessel
    wall = patches.Circle((0, 0), radius=r_wall, facecolor='b', edgecolor='k', alpha=0.3)
    ax.add_patch(wall)

    # Plot tile radii etc
    for key in ['R_T1', 'R_T4', 'R_T5', 'R_T5_top', 'R_HL04']:
        r = surface_radii[key]
        wall = patches.Circle((0, 0), radius=r, facecolor=None, fill=False, edgecolor='k', ls='--', alpha=0.3)
        ax.add_patch(wall)

    # Lines between sectors
    for i in np.arange(n_sectors):
        x, y = r_phi_to_xy(r_wall, i*360/n_sectors, phi_in_deg=True)
        ax.plot([0, x], [0, y], ls='--', c='k', lw=1)

    # Sector numbers
    for i in np.arange(n_sectors):
        x, y = r_phi_to_xy(r_wall*0.9, 90-(i+0.5)*360/n_sectors, phi_in_deg=True)
        plt.text(x, y, f'{i+1}', horizontalalignment='center', verticalalignment='center')

    # Phi labels
    for i in np.arange(4):
        phi = i*360/4
        x, y = r_phi_to_xy(r_wall, phi, phi_in_deg=True)
        label = f'$\phi={phi:0.0f}^\circ$'
        # annotate_axis(ax, label, x, y, fontsize=16, color='k')
        plt.text(x, y, label, horizontalalignment='left', verticalalignment='bottom')

    ax_scale = 1.2
    ax.set_xlim(-r_wall*ax_scale, r_wall*ax_scale)
    ax.set_ylim(-r_wall*ax_scale, r_wall*ax_scale)
    ax.set_aspect(1)
    ax.set_xlabel(r'x [m]')
    ax.set_ylabel(r'y [m]')
    plt.tight_layout()

    return fig, ax

def plot_camera_vectors(ax):
    for camera in camera_views:
        pupil = camera_views[camera]['pupil']
        view = camera_views[camera]['view']
        color = camera_views[camera]['color']
        x_centre = (pupil['x'], view['x'])
        y_centre = (pupil['y'], view['y'])
        ax.plot(pupil['x'], pupil['y'], markersize=8, marker='s', color=color, alpha=0.7)
        arrowplot(ax, x_centre, y_centre, c=color, narrs=1, hl=0.005, direc='pos', dspace=1, alpha=0.8)

def r_phi_to_xy(r, phi, phi_in_deg=True):
    if phi_in_deg:
        phi = np.deg2rad(phi)
    x = r * np.cos(phi)
    y = r * np.sin(phi)
    return (x, y)

if __name__ == '__main__':

    fig, ax = plot_mast_top_down()
    plot_camera_vectors(ax)

    save_fig('./plots/mast_u_camera_views.png')
    plt.show()
    pass