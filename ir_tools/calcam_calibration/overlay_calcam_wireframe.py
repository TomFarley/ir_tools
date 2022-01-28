#!/usr/bin/env python

"""


Created: 
"""

import logging, time
from pathlib import Path
import functools

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

import calcam

from fire.plotting import plot_tools

logger = logging.getLogger(__name__)

def ndarray_0d_to_scalar(array):
    """Convert 0D (single element) array to a scalar number (ie remove nested array)"""
    out = array
    if isinstance(array, (np.ndarray, xr.DataArray)) and array.ndim == 0:
        out = array.item()
    return out

def angles_to_convention(angles, units_input='radians', units_output='degrees', negative_angles=False,
                         cast_scalars=True):
    """Convert angles between radians and degrees and from +/-180 deg range to 0-360 range

    Args:
        angles: Array of angles
        units_input: Units of input data (radians/degrees)
        units_output: Units angles should be converted to (radians/degrees)
        negative_angles: Whether angles should be in range  +/-180 deg or 0-360 range
        cast_scalars: If output is 0D array cast to scalar float
    Returns:

    """
    if units_input in ('radians', 'rad'):
        units_input = 'radians'
    if units_output in ('degrees', 'deg'):
        units_output = 'degrees'

    if units_input not  in ('radians', 'degrees'):
        raise ValueError(f'Invalid input angle units: {units_input}')
    if units_output not in ('radians', 'degrees'):
        raise ValueError(f'Invalid output angle units: {units_output}')

    if (units_input == 'radians') and (units_output == 'degrees'):
        angles = np.rad2deg(angles)
    elif (units_input == 'degrees') and (units_output == 'radians'):
        angles = np.deg2rad(angles)

    shift = 360 if (units_output == 'degrees') else 2 * np.pi
    if (not negative_angles):
        angles = np.where(angles < 0, angles+shift, angles)
    else:
        half_circle = 180 if (units_output == 'degrees') else np.pi
        angles = np.where(angles > half_circle, angles-shift, angles)

    if cast_scalars:
        angles = ndarray_0d_to_scalar(angles)

    return angles

def cartesian_to_toroidal(x, y, z=None, angles_in_deg=False, angles_positive=True):
    """Convert cartesian coordinates to toroidal coordinates

    Args:
            x           : x cartesian coordinate(s)
            y           : y cartesian coordinate(s)
            z           : (Optional) z cartesian coordinate(s) - not used
        angles_in_deg  : Whether to convert phi output from radians to degrees
        angles_positive: Whether phi values should be in range positive [0, 360]/[[0,2pi] else [-180, +180]/[-pi, +pi]

    Returns: (r, phi, theta)

    """
    #TODO: Update call signature to be more inline with angles_to_convention()?
    r = np.hypot(x, y)
    phi = np.arctan2(y, x)  # Toroidal angle 'ϕ'

    # Poloidal angle 'ϑ'
    if z is not None:
        theta = np.arctan2(z, r)
    else:
        theta = np.full_like(x, np.nan)

    units = 'degrees'*angles_in_deg + 'radians' * (not angles_in_deg)
    phi = angles_to_convention(phi, units_input='radians', units_output=units, negative_angles=(not angles_positive))
    theta = angles_to_convention(theta, units_input='radians', units_output=units, negative_angles=(not angles_positive))

    return r, phi, theta

@functools.lru_cache(maxsize=2)
def get_calcam_cad_obj(model_name='MAST', model_variant='Detailed', check_fire_cad_defaults=True):
    logger.debug(f'Loading CAD model...');
    t0 = time.time()
    # TODO: Add error messages directing user to update Calcam CAD definitions in settings GUI if CAD not found
    # print(dir(calcam))
    try:
        cad_model = calcam.CADModel(model_name=model_name, model_variant=model_variant)
    except ValueError as e:
        raise e
    except AttributeError as e:
        if str(e) == "module 'calcam' has no attribute 'CADModel'":
            logger.warning('Calcam failed to import calcam.cadmodel.CADModel presumably due to vtk problem')
            import cv2
            import vtk
        raise
    logger.debug(f'Setup CAD model object in {time.time()-t0:1.1f} s')
    return cad_model


@functools.lru_cache(maxsize=2)
def get_surface_coords(calcam_calib, cad_model, image_coords='Original', phi_positive=True, intersecting_only=False,
                       exclusion_radius=0.10, remove_long_rays=False, outside_vesel_ray_length=10,
                       outside_view_raylengths=None):
    if image_coords.lower() == 'display':
        image_shape = calcam_calib.geometry.get_display_shape()
    else:
        image_shape = calcam_calib.geometry.get_original_shape()
    # Use calcam convention: image data is indexed [y, x], but image shape description is (nx, ny)
    x_pix = np.arange(image_shape[0])
    y_pix = np.arange(image_shape[1])
    coord_color = np.array(['Red', 'Green', 'Blue'])
    coord_color_alpha = np.array(['Red', 'Green', 'Blue', 'Alpha'])
    data_out = xr.Dataset(coords={'x_pix': x_pix, 'y_pix': y_pix,
                                  'color': ('color', coord_color), 'color_alpha': ('color_alpha', coord_color_alpha)})

    # Get wireframe image of CAD from camera view
    # Steps copied from calcam gui
    # orig_colours = cad_model.get_colour()
    # cad_model.set_wireframe(True)
    # cad_model.set_colour((0, 0, 1))
    # overlay = calcam.render_cam_view(cad_model, calcam_calib, transparency=True, verbose=False, aa=2)
    # cad_model.set_colour(orig_colours)
    # cad_model.set_wireframe(False)


    cad_model.set_flat_shading(False)  # lighting effects
    cad_model.set_wireframe(True)
    # cad_model.set_linewidth(3)
    color = cad_model.get_colour()
    cad_model.set_colour((1, 0, 0))
    # print(f'Wireframe original color {color} changed to {cad_model.get_colour()}')
    wire_frame = calcam.render_cam_view(cad_model, calcam_calib, coords=image_coords, transparency=True, verbose=False)
    wire_frame_gray = np.max(wire_frame, axis=2)

    logger.debug(f'Getting surface coords...'); t0 = time.time()

    ray_data = calcam.raycast_sightlines(calcam_calib, cad_model, coords=image_coords, force_subview=None,
                                         exclusion_radius=exclusion_radius, intersecting_only=intersecting_only)
    # TODO: Set sensor subwindow if using full sensor calcam calibration for windowed view
    # ray_data.set_detector_window(window=(Left,Top,Width,Height))
    logger.debug(f'Setup CAD model and cast rays in {time.time()-t0:1.1f} s')

    surface_coords = ray_data.get_ray_end(coords=image_coords)
    ray_lengths = ray_data.get_ray_lengths(coords=image_coords)
    # open rays that don't terminate in the vessel - should no longer be required now calcam.raycast_sightlines has
    # the keyword intersecting_only=True
    mask_bad_data = ray_lengths > outside_vesel_ray_length
    # if remove_long_rays and (not intersecting_only):
    #     nsigma = calc_outlier_nsigma_for_sample_size(ray_lengths.size, n_outliers_expected=1)
    #     thresh_long_rays = find_outlier_intensity_threshold(ray_lengths, nsigma=nsigma)
    #     mask_long_rays = ray_lengths > thresh_long_rays
    #     mask_bad_data += mask_long_rays
    if outside_view_raylengths is not None:
        # Eg MAST-U RIR view of T2 sees a small range of depths - any longer rays are due to holes in CAD
        mask_long_rays = ray_lengths > outside_view_raylengths
        mask_bad_data += mask_long_rays

    ind_bad_data = np.where(mask_bad_data)
    surface_coords[ind_bad_data[0], ind_bad_data[1], :] = np.nan
    ray_lengths[mask_bad_data] = np.nan
    if len(ind_bad_data[0]) > 0:
        logger.info(f'Spatial coords for {len(ind_bad_data[0])} pixels set to "nan" due to holes in CAD model')
        if intersecting_only:
            logger.warning(f'Excessively long rays (>{outside_vesel_ray_length} m) despite intersecting_only=True')

    x = surface_coords[:, :, 0]
    y = surface_coords[:, :, 1]
    z = surface_coords[:, :, 2]
    r, phi, theta = cartesian_to_toroidal(x, y, z, angles_in_deg=False, angles_positive=phi_positive)

    data_out['x_im'] = (('y_pix', 'x_pix'), x)
    data_out['y_im'] = (('y_pix', 'x_pix'), y)
    data_out['z_im'] = (('y_pix', 'x_pix'), z)
    data_out['R_im'] = (('y_pix', 'x_pix'), r)
    data_out['phi_im'] = (('y_pix', 'x_pix'), phi)  # Toroidal angle 'ϕ'
    data_out['phi_deg_im'] = (('y_pix', 'x_pix'), np.rad2deg(phi))  # Toroidal angle 'ϕ' in degrees
    data_out['theta_im'] = (('y_pix', 'x_pix'), theta)
    data_out['ray_lengths_im'] = (('y_pix', 'x_pix'), ray_lengths)  # Distance from camera pupil to surface
    # Indices of sub calibrations due to mirrors etc
    data_out['subview_mask_im'] = (('y_pix', 'x_pix'), calcam_calib.get_subview_mask(coords=image_coords))
    data_out['bad_cad_coords_im'] = (('y_pix', 'x_pix'), mask_bad_data.astype(int))  # Pixels seeing holes in CAD model
    # spatial_res = calc_spatial_res(x, y, z, res_min=1e-4, res_max=None)
    # for key, value in spatial_res.items():
    #     data_out[key] = (('y_pix', 'x_pix'), value)
    # Add labels for plots
    # data_out['spatial_res_max'].attrs['standard_name'] = 'Spatial resolution'
    # data_out['spatial_res_max'].attrs['units'] = 'm'
    # Just take red channel of wireframe image
    data_out['wire_frame'] = (('y_pix', 'x_pix', 'coord_color_alpha'), wire_frame)  # wire_frame[:, :, 0])
    data_out['wire_frame_gray'] = (('y_pix', 'x_pix'), wire_frame_gray)  # wire_frame[:, :, 0])

    return data_out

def plot_wireframe(ax, calcam_calib, cad_model=None, overlay_wireframe=True, alpha=0.7, cmap='Reds'):

    if (calcam_calib is not None) and overlay_wireframe:
        if cad_model is None:
            cad_model = get_calcam_cad_obj()

        spatial_data = get_surface_coords(calcam_calib, cad_model)

        wire_frame = spatial_data['wire_frame']
        # wire_frame = spatial_data['wire_frame_gray']

        if wire_frame.ndim > 2:
            wire_frame[:, :, 1:2] = 0  # Zero out green and blue

        wireframe_artist = ax.imshow(wire_frame, interpolation='none', origin='upper', alpha=alpha, cmap=cmap)  # Cmap ignored for RCB(A)
    else:
        wireframe_artist = None

    return wireframe_artist

def annimate_uda_movie():
    NotImplementedError()

def annimate_mraw_movie(path_fn_mraw_pattern, n=None, transforms = ('transpose', 'reverse_y'), calcam_calib=None,
                        shot=None):
    """
    eg path_fn_mraw_pattern = f'/projects/SOL/Data/Cameras/SA1/{pulse}/C001H001S0001/C001H001S0001-{{n:02d}}.mraw'

    :param path_fn_mraw_pattern:
    :return:
    """
    from pyipx_examples import mraw_examples

    # Print out the frame ranges that are stored in each mraw file for this shot
    meta_data = mraw_examples.get_mraw_file_info(path_fn_mraw_pattern, transforms=transforms)
    # print(meta_data['mraw_files'])

    # To read the whole movie (slow - 27000 frames) pass n = None
    frame_numbers, frame_times, frame_data = mraw_examples.read_mraw_movie(path_fn_mraw_pattern, n=n, transforms=transforms)
    # print(data.shape)

    label_substitutions = {'t': np.array(frame_times) * 1e3, 'shot': np.full_like(frame_times, shot, dtype=object)}

    annimate_movie_data(frame_data, frame_times, frame_numbers, calcam_calib=calcam_calib, label_substitutions=label_substitutions)

def annimate_ipx_movie(path_fn_ipx):
    from fire.plugins.movie_plugins import ipx
    frame_numbers, frame_times_all, frame_data = ipx.read_movie_data(path_fn_ipx)

    annimate_movie_data(frame_data, frame_times_all, frame_numbers)

def annimate_raw_movie(path_fn_raw):
    from fire.plugins.movie_plugins import raw_movie
    frame_numbers, frame_times_all, frame_data = raw_movie.read_movie_data(path_fn_raw)

    annimate_movie_data(frame_data, frame_times_all, frame_numbers)

def get_vmin_vmax(frame_data, cbar_range=None):
    if (cbar_range is not None):
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

    return vmin, vmax, extend

def initialise_annimation_image(ax, frame_data, i_start=0, cmap='gray', cbar=True, cbar_range=None, cbar_label=None,
                                axes_off=True, frame_label='', label_substitutions=None):
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    img_data = frame_data[i_start]
    img = ax.imshow(img_data, cmap=cmap)

    vmin, vmax, extend = get_vmin_vmax(frame_data, cbar_range=cbar_range)

    if cbar:
        div = make_axes_locatable(ax)
        ax_cbar = div.append_axes('right', '5%', '5%')
        fig = ax.figure
        cbar = fig.colorbar(img, cax=ax_cbar, extend=extend, label=cbar_label)

    frame_label_i = frame_label.format(**{k: v[i_start] for k, v in label_substitutions.items()})
    frame_label_artist = plot_tools.annotate_axis(ax, frame_label_i, loc='top_left', box=False, color='white')

    if axes_off:
        ax.set_axis_off()

    artists = dict(img=img, cbar=cbar, frame_label_artist=frame_label_artist)

    return artists

def annimate_movie_data(frame_data, frame_times=None, frame_numbers=None, ax=None, duration=10, interval=None,
                        frame_label='{shot} $t=${t:0.1f} ms', cbar_label=None, label_substitutions=None,
                        cmap='gray', axes_off=True, fig_kwargs=None,
                        n_start=None, n_end=None, nth_frame=1, cbar=True, cbar_range=None,
                        save_kwargs=None, save_path_fn=None,
                        calcam_calib=None, overlay_wireframe=True,
                        show=True):
    from matplotlib.animation import FuncAnimation

    if frame_numbers is None:
        frame_numbers = np.arange(len(frame_data))

    if fig_kwargs is None:
        fig_kwargs = {}

    nframes_total = len(frame_data)
    if n_start is None:
        n_start = 0
    if n_end is None:
        n_end = nframes_total - 1
    nframes_animate = int((n_end - n_start) / nth_frame)
    frame_nos_animate = np.arange(n_start, n_end + 1, nth_frame, dtype=int)

    logger.info(f'Plotting matplotlib animation ({nframes_animate} frames)')

    fig, ax, ax_passed = plot_tools.get_fig_ax(ax=ax, **fig_kwargs)

    if interval is None:
        if (duration is None):  # duration fo whole movie/animation in s
            interval = 200  # ms
        else:
            interval = duration / nframes_animate * 1000

        # tx = ax.set_title(f'Frame 0/{nframes_animate-1}')

    vmin, vmax, extend = get_vmin_vmax(frame_data, cbar_range=cbar_range)

    artists = initialise_annimation_image(ax, frame_data=frame_data, i_start=frame_nos_animate[0], cmap=cmap, cbar=cbar,
                                          cbar_range=cbar_range, cbar_label=cbar_label, frame_label=frame_label,
                                          label_substitutions=label_substitutions)

    wireframe_artist = plot_wireframe(ax, calcam_calib, overlay_wireframe=overlay_wireframe)

    img = artists['img']
    frame_label_artist = artists['frame_label_artist']

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
        frame_label_i = frame_label.format(**{k: v[frame_no] for k, v in label_substitutions.items()})
        frame_label_artist.set_text(frame_label_i)
        # return img, cbar, tx
        # return ln,

    anim = FuncAnimation(fig, update, frames=frame_nos_animate, fargs=(vmin, vmax),  # np.linspace(0, 2 * np.pi, 128),
                        interval=interval, # init_func=init,
                        blit=False)

    if save_path_fn is not None:
        save_path_fn = Path(save_path_fn).expanduser().resolve()
        try:
            kwargs = dict(fps=30)
            if save_kwargs is not None:
                kwargs.update(save_kwargs)
            if save_path_fn.suffix == '.gif':
                anim.save(str(save_path_fn), writer='imagemagick', **kwargs)
                          # savefig_kwargs=dict(bbox_inches='tight', transparent=True))  # transparent makes blury
            else:
                Writer = anim.writers['ffmpeg']
                kws = dict(codec='ffv1', fps=15, bitrate=1e6)  # codec='ffv1', codec='mpeg4',
                kws.update(kwargs)
                writer = Writer(**kws)
                #
                dpi = 100
                with writer.saving(fig, save_path_fn, dpi):
                    # code to plot/update figure
                    writer.grab_frame(facecolor='k')
        except Exception as e:
            logger.exception(f'Failed to save matplotlib animation gif to {save_path_fn}')
        else:
            logger.info(f'Saved animation gif to {save_path_fn}')

    if show:
        plt.show()

    return fig, ax, anim

def overplot_calibration_wireframe_on_sa1_movie_range(path_fn_calib, shots):
    # This is the location for the fast 100kHz visible camera data that isn't accessible via UDA.
    # Need to use pyIpx to read the mraw files directly.
    path_fn_mraw_pattern = '/projects/SOL/Data/Cameras/SA1/{shot}/C001H001S0001/C001H001S0001-{{n:02d}}.mraw'

    calcam_calib = calcam.Calibration(path_fn_calib)

    # Plot a subset of frames (every 10th frame over first 1000 frames) to speed up reading and plotting movie
    frame_numbers = np.arange(0, 1000, 10)

    # Plot the same calcam calibration wireframe on a series of movies
    for shot in shots:
        path_fn_mraw = path_fn_mraw_pattern.format(shot=shot)
        try:
            annimate_mraw_movie(path_fn_mraw, n=frame_numbers, calcam_calib=calcam_calib, shot=shot)
        except AssertionError as e:
            pass  # Skip shots without a movie
    pass


if __name__ == '__main__':
    # fn = '/projects/SOL/Data/Cameras/IR/RIT/2021-08-24/None.RAW'
    # fn = '/projects/SOL/Data/Cameras/IR/RIT/2021-08-24/44793.RAW'
    # fn = '/projects/SOL/Data/Cameras/SA1/{shot}/C001H001S0001/C001H001S0001-00.mraw'

    # One of my calibrations for 29852
    path_fn_calib = '/home/tfarley/calcam2/calibrations/p29852-f1807-t0.21808-ae_ga_sh-v1-k23_diss.ccc'

    shot_start = 29811
    n_shots = 300
    shots = np.arange(shot_start, shot_start+n_shots)

    overplot_calibration_wireframe_on_sa1_movie_range(path_fn_calib, shots)