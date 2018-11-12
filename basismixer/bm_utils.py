import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d


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
        Smoothed parameter (this is only returned if `return_smoothed_param` is True)
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


if __name__ == '__main__':
    import json
    from performance_codec import get_unique_onsets
    fn = '../bm_files/chopin_op10_No3_bm_magaloff.txt'
    config_file = json.load(open(fn.replace('.txt', '.json')))

    bm_data = np.loadtxt(fn)
    onsets = bm_data[:, 1]
    unique_onsets, unique_onset_idxs = get_unique_onsets(onsets)

    vel_trend = np.array([bm_data[ix, 3].mean() for ix in unique_onset_idxs])
    vt_trendless, vt_smoothed = remove_trend(vel_trend, unique_onsets, 'savgol',
                                             return_smoothed_param=True)
    x = unique_onsets
    y = vel_trend
    yhat = vt_smoothed

    plt.plot(x, y / vel_trend.mean())
    plt.plot(x, yhat / vel_trend.mean(), color='red')
    plt.plot(x, vt_trendless / vel_trend.mean(), color='black')
    plt.show()
