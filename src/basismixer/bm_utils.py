"""
    Utils for the performance codec
"""
import numpy as np
import scipy.signal as signal
from scipy.interpolate import interp1d


def get_unique_onsets(onsets):
    """Get the unique score positions given a list of onsets.

    Parameters
    ----------
    onsets : np.ndarray
        1D array of floats containing the score onset time for each note
        in a score.

    Returns
    -------
    unique_onsets : np.ndarray
        Unique score onset times (in ascending order). `unique_onsets`
        should be identical to `onsets` for strictly monophonic pieces
        (and assuming that the onsets are ordered).
    unique_onset_idxs : list of np.ndarrays
        list contaning the indices of the notes corresponding to each
        unique score position (in the same order, e.g.
        `unique_onset_idxs[0]` corresponds to the indices of the notes
         occurring at `unique_onsets[0]`).
    """
    # Get unique score positions
    unique_onsets = np.unique(onsets)
    unique_onsets.sort()

    # List of indices corresponding to each of the unique score positions
    unique_onset_idxs = [np.where(onsets == u)[0] for u in unique_onsets]

    return unique_onsets, unique_onset_idxs


def standardize(array):
    """Normalize array such that the mean
    of its elements is zero and its variance is 1.

    If the variance of the array is zero, only makes the
    array zero mean.

    Parameters
    ----------
    array : np.ndarray
        Array to be standardized

    Returns
    -------
    np.ndarray
        Standardized array
    """
    if not np.isclose(array.std(), 0):
        return (array - array.mean()) / (array.std())
    else:
        return (array - array.mean())


def minmax_normalize(array):
    """Normalize array to lie between 0 and 1.

    Parameters
    ----------
    array : np.ndarray
        Array to be normalized

    Returns
    -------
    np.ndarray
        Normalized array
    """
    return (array - array.min()) / (array.max() - array.min())


def sigmoid(x):
    """Sigmoid function (in Numpy).
    According to https://stackoverflow.com/a/25164452,
    this implementation is faster than `scipy.stats.logistic` or
    `scipy.special.expit`.


    Parameters
    ----------
    x : float or np.ndarray
        Input of the function.

    Returns
    -------
    float or np.ndarray
        Output of the sigmoid
    """
    return 1 / (1 + np.exp(-x))


# for convenience
SIGMOID_1 = sigmoid(1.0)


def sgf_smooth(y, ws=51, order=5):
    """Smooth curve using Savitzky-Golay filter

    Parameters
    ----------
    y : np.ndarray
        Data to be filtered.
    ws : int, optional
        Window size of the filter window (must be a possitive odd integer).
        (Default 51)
    order : int, optional
        Order of the polynomial used to fit the samples. (default is 5).

    Returns
    -------
    np.ndarray
        Filtered data.
    """
    return signal.savgol_filter(y, ws, order)


def ma_smooth(y, order=15):
    """Smooth curve using Mooving Average filter

    Parameters
    ----------
    y : np.ndarray
        Data to be filtered.
    order : int, optional
        Order of the Moving average. Default is 15.

    Returns
    -------
    np.ndarray
        Filtered data.

    """
    box = np.ones(order) / order
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth


def remove_trend(parameter, unique_onsets, smoothing='savgol',
                 return_smoothed_param=False, *args, **kwargs):
    """Remove the trend from an onset-wise expressive parameter

    Parameters
    ----------
    parameter : np.ndarray
        Onset-wise expressive parameter (predicted by the BM)
    unique_onsets : array
        Score positions (should be the same length as `parameter`)
    smoothing : str
        Smoothing algorithm. Should be 'savgol' or 'ma' (default 'savgol').
        Additional positional and keyword arguments can be passed to the
        corresponding method.
    return_smoothed_param : bool, optional
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
    """Compute the range (maximal and minmal values) of the expressive parameters
    for later rescaling the performance parameters to lie between 0 and 1 in the
    visualization.

    Parameters
    ----------
    score_dict : dict
       Dictionary containing the score information (as generated by
       `basismixer.performance_codec.load_bm_preds`)
    max_scaler : float
       Maximal level of the Knob controller
    eps : float, optional
       Epsilon for numerical precision. Default is 1e-10
    remove_trend_vt : bool, optional
       If `True`, computes the scaling for velocity trend assuming that
       the parameter was smoothed. Default is `True`.

    Returns
    -------
    vt_max : float
        Maximal value of the MIDI velocity trend.
    vt_min : float
        Minimal value of the MIDI velocity trend.
    vd_max : float
        Maximal value of the MIDI velocity deviations.
    vd_min : float
        Minimal value of the MIDI velocity deviations.
    lbpr_max : float
        Maximal value of the log beat period ratio.
    lbpr_min : float
        Minimal value of the log beat period ratio.
    tim_max : float
        Maximal value of the timing deviations.
    tim_min : float
        Minimal value of the timing deviations.
    lart_max : float
        Maximal value of the log articulation ratio.
    lart_mi : float
        Minimal value of the log articulation ratio.
    """

    # Get the parameters from the score_dict
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

    # Get maximal and minimal values
    if remove_trend_vt:
        # If the trend is removed, use linear scaling
        vt_max = vel_trend.max() * max_scaler
        vt_min = vel_trend.min() * max_scaler
    else:
        # If the trend is not removed, use exponential
        # scaling (the values should be between 0 and 1)
        vt_max = vel_trend.max() ** max_scaler
        vt_min = vel_trend.min() ** max_scaler

    vd_max = max_scaler * vel_devc.max()
    vd_min = max_scaler * vel_devc.min()

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
    """Compute the size of the visualization for notes corresponding
    to the current score onset.

    vt : float
        MIDI velocity trend for all notes in the current onset
    vd : np.ndarray
        MIDI velocity deviations for each note in the current onset
        (each value corresponds to a note)
    lbpr : float
        Log Beat Period Ratio for all notes in the current onset
    tim : np.ndarray
        Timing deviations for each note in the current onset.
    lart : np.ndarray
        Log articulation for each note in the current onset.
    vis_scaling_factors : tuple
        The maximal and minimal values for the scaling for each parameter
        (computed using `get_vis_scaling_factors`). The tuple contains
        all 10 parameters returned by `get_vis_scaling_factors`.
    eps : float, optional
        Small epsilon for numerical precision (default is 1e-10).
    remove_trend_vt : bool, optional
        Use correct scaling if the MIDI velocity trend was smoothed.

    Returns
    -------
    vts : float
        Size of the column visualizing MIDI velocity trend (should be between
        0 and 1).
    vds : float
        Size of the column visualizing MIDI velocity deviations (should be between
        0 and 1).
    lbprs : float
        Size of the column visualizing Log Beat Period Ratio (should be between 0
        and 1).
    tims : float
        Size of the column visualizing timing deviations (should be between 0
        and 1).
    larts : float
        Size of the column visualizing log articulation ration (should be between
        0 and 1).
    """
    # Unpack range limits of the parameters
    (vt_max, vt_min, vd_max, vd_min, lbpr_max, lbpr_min,
     tim_max, tim_min, lart_max, lart_min) = vis_scaling_factors

    # Compute scaling for each parameter
    if remove_trend_vt:
        # Use linear if the trend was removed
        vts = _scale_vis(vt, vt_min, vt_max)
    else:
        # Use logarithmic scaling if the trend was not removed
        vts = _scale_vis(np.log2(vt + eps), vt_min, vt_max)

    vds = _scale_vis(vd, vd_min, vd_max)
    lbprs = _scale_vis(lbpr, lbpr_min, lbpr_max)
    tims = _scale_vis(tim, tim_min, tim_max)
    larts = _scale_vis(lart, lart_min, lart_max)

    return vts, vds, lbprs, tims, larts


def _scale_vis(x, x_min, x_max):
    """Compute size of the column of the visualization of a parameter
       (so that parameters lie between 0 and 1).

    Parameters
    ----------
    x : float or np.ndarray
        The value of the expressive parameters
    x_min : float
        Minimal value of the parameter
    x_max : float
        Maximal value of the parameters

    Returns
    xs : float
        Size of the visualization column.
    """
    # Use the mean of the values if they are an array
    if isinstance(x, float):
        x_p = x
    elif isinstance(x, np.ndarray):
        x_p = np.mean(x)

    # If the parameters are close to 0 (close to the mean deadpan performance),
    # the scale of the parameters is 0.5 (half of the column).
    if np.isclose(x_p, 0):
        xs = 0.5
    elif x_p > 0:
        # If the parameters are larger than the mean, make them lie between
        # 0.5 and 1.
        # xs = 0.5 * ((x_p - x_min) / (x_max - x_min) + 1)
        xs = 0.5 * x_p / x_max + 0.5
    elif x_p < 0 and not np.isclose(x_min, 0):
        # If the parameters are smaller than the mean, make them lie between
        # 0 and 0.5
        # xs = -0.5 * (x_p - x_min) / (x_min)
        xs = 0.5 * x_p / x_min
    else:
        # Do not break in case a numerical error (such as the parameters being
        # NAN).
        # Perhaps it would be better to handle this case somewhere else...
        xs = 0.5

    return xs
