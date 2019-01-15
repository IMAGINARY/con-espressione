"""
    Utils for the performance codec
"""
import numpy as np
import scipy.signal as signal
from scipy.interpolate import interp1d


def get_unique_onsets(onsets):
    # Get unique score positions
    unique_onsets = np.unique(onsets)
    unique_onsets.sort()

    # List of indices corresponding to each of the unique score positions
    unique_onset_idxs = [np.where(onsets == u)[0] for u in unique_onsets]

    return unique_onsets, unique_onset_idxs


def standardize(array):
    if not np.isclose(array.std(), 0):

        return (array - array.mean()) / (array.std())
    else:
        return (array - array.mean())


def minmax_normalize(array):
    return (array - array.min()) / (array.max() - array.min())


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def sgf_smooth(y, ws=51, order=5):
    """Savitzky-Golay filter
    """
    return signal.savgol_filter(y, ws, order)


def ma_smooth(y, order=15):
    """Mooving average filter
    """
    box = np.ones(order) / order
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth


def remove_trend(parameter, unique_onsets, smoothing='savgol',
                 return_smoothed_param=False, *args, **kwargs):
    """Remove the trend from an onset-wise expressive parameter

    Parameters
    ----------
    parameter : array
        Onset-wise expressive parameter (predicted by the BM)
    unique_onsets : array
        Score positions (should be the same length as `parameter`)
    smoothing : str
        Smoothing algorithm. Should be 'savgol' or 'ma' (default 'savgol').
        Additional positional and keyword arguments can be passed to the
        corresponding method.
    return_smoothed_param : bool
        Return smoothed version of the expressive parameter (for debugging
        purposes). Default is `False`.

    Returns
    -------
    parameter_trendless : array
        Parameter with the trend removed.
    parameter_smoothed : array
        Smoothed parameter (this is only returned if `return_smoothed_param`
        is True)
    """
    # Interpolation function for the parameter
    param_func = interp1d(unique_onsets, parameter,
                          kind='zero', bounds_error=False,
                          fill_value=(parameter[0], parameter[-1]))

    # Interpolate values of the parameter
    x = np.linspace(unique_onsets.min(), unique_onsets.max(),
                    len(unique_onsets) * 4)
    _parameter = param_func(x)

    # Smooth the parameter using a filter
    if smoothing == 'savgol':
        # Use Savitzky-Golay filter
        _param_smooth = sgf_smooth(_parameter, *args, **kwargs)
    elif smoothing == 'ma':
        # Use Moving average filter
        _param_smooth = ma_smooth(_parameter, *args, **kwargs)
    else:
        raise ValueError(
            '`smoothing should be "savgol" or "ma". Given {0}'.format(smoothing))

    # Interpolation function for the smoothed data
    param_smooth_func = interp1d(x, _param_smooth, kind='linear',
                                 fill_value='interpolate')

    parameter_smoothed = param_smooth_func(unique_onsets)
    # Remove the trend from the parameter
    parameter_trendless = parameter_smoothed - parameter

    if return_smoothed_param:
        return parameter_trendless, parameter_smoothed
    else:
        return parameter_trendless


def get_vis_scaling_factors(score_dict, max_scaler, eps=1e-10,
                            remove_trend_vt=True):

    vel_trend = []
    vel_dev = []
    log_bpr = []
    timing = []
    log_art = []
    for on in score_dict:
        (pitch, ioi, dur,
         vt, vd, lbpr,
         tim, lart, mel, ped) = score_dict[on]

        if vt is not None:
            vel_trend.append(vt)
        if vd is not None:
            vel_dev.append(vd)
        if lbpr is not None:
            log_bpr.append(lbpr)
        if tim is not None:
            timing.append(tim)
        if lart is not None:
            log_art.append(lart)

    vel_trend = np.array(vel_trend)
    # vel_trend /= vel_trend.mean()

    vel_devc = np.hstack(vel_dev)
    log_bpr = np.array(log_bpr)
    timingc = np.hstack(timing)
    log_artc = np.hstack(log_art)

    if remove_trend_vt:
        vt_max = vel_trend.max() * max_scaler
        vt_min = vel_trend.min() * max_scaler
    else:
        vt_max = vel_trend.max() ** max_scaler
        vt_min = vel_trend.min() ** max_scaler

    vd_max = - max_scaler * vel_devc.max()
    vd_min = - max_scaler * vel_devc.min()

    lbpr_max = max_scaler * log_bpr.max()
    lbpr_min = max_scaler * log_bpr.min()

    tim_max = max_scaler * timingc.max()
    tim_min = max_scaler * timingc.min()

    lart_max = max_scaler * log_artc.max()
    lart_min = max_scaler * log_artc.min()

    return (vt_max, vt_min, vd_max, vd_min, lbpr_max, lbpr_min,
            tim_max, tim_min, lart_max, lart_min)


def compute_vis_scaling(vt, vd, lbpr, tim, lart,
                        vis_scaling_factors, eps=1e-10,
                        remove_trend_vt=True):
    (vt_max, vt_min, vd_max, vd_min, lbpr_max, lbpr_min,
     tim_max, tim_min, lart_max, lart_min) = vis_scaling_factors

    if remove_trend_vt:
        vts = _scale_vis(vt, vt_min, vt_max)
    else:
        vts = _scale_vis(np.log2(vt + eps), vt_min, vt_max)

    vds = _scale_vis(- vd, vd_min, vd_max)
    lbprs = _scale_vis(lbpr, lbpr_min, lbpr_max)
    tims = _scale_vis(tim, tim_min, tim_max)
    larts = _scale_vis(lart, lart_min, lart_max)

    return vts, vds, lbprs, tims, larts


def _scale_vis(x, x_min, x_max):

    if isinstance(x, float):
        x_p = x
    elif isinstance(x, np.ndarray):
        x_p = np.mean(x)

    if np.isclose(x_p, 0):
        xs = 0.5
    elif x_p > 0:
        xs = 0.5 * ((x_p - x_min) / (x_max - x_min) + 1)
    elif x_p < 0:
        xs = -0.5 * (x_p - x_min) / (x_min)

    return xs
