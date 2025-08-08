"""
Author: Victor Gutgesell
Date of creation: 09.11.2024

ECG helpers is a collection of functions that help to analyze ECG data.
"""
import pandas as pd
# Import global packages ------------------------------------------------
from matplotlib.pyplot import axes, subplots
from pandas import Series
from numpy.core.multiarray import ndarray
from scipy.signal import find_peaks, butter, filtfilt, windows, welch
from numpy import (ndarray, array, arange, min, fft, mean, diff, abs, quantile,
                   int_, integer, linalg, convolve, conj, argmax, sum, sqrt)

# Static functions -----------------------------------------
"""
Function to apply a bandpass filter over a signal y. It uses fft transformation to filter.
The bandpass filter will by default assume a sampling frequency of 1. 
Give the timestamp argument if the fs is different.
The fs will be calculated by taking the mean of the differences between each timestamp. 
Make sure everything is in seconds.
"""


def frequency_filtering_fft(y: ndarray | list | Series,
                            t: ndarray | list | Series = None,
                            upper: float | int | None = None,
                            lower: float | int | None = None,
                            reconstruction_mode: str = 'all') -> ndarray:
    """
    This function takes an input signal y in time domain and funnels it through a frequency filter to return
    the filtered time domain signal.

    :param y: array like - time domain signal which is to be filtered.
    :param t: array like - timestamps of y in seconds - timestamps do not have to be exactly equidistant
                but should be close to it for best results.
                If no timestamps are provided, the signal datapoints are assumed to be spaced each 1s apart.
                Needless to say, this will result in a weird result if you expect to filter specific frequency.
    :param upper: float - upper bound of the bandpass in Hz
    :param lower: float - lower bound of the bandpass in Hz
    :param reconstruction_mode: define if reconstruction mode is 'all' or only on positive frequencies
    :return: y_filtered: array like - filtered time domain signal
    :return: t_filtered timestamps of y_filtered
    """

    if t is None:
        t = arange(len(y))
    else:
        if len(y) != len(t):  # Checks if t and y match, otherwise it returns raw signal
            raise ValueError(f'Dimension mismatch, length of y ({len(y)}) must be equal to length of t ({len(t)})')

    t_filtered = array(t - min(t))  # Setting time-series to start at zero
    # Performing the FFT on the resampled signal
    N = len(y)
    X = fft.fft(y, N)  # FFT of signal Y
    # Returns frequencies in Hz -> Note the term (1/mean(diff(t))) accounts for the sampling frequency
    freq = fft.fftfreq(N) * (1 / mean(diff(t_filtered)))

    if reconstruction_mode == 'all':
        freq = abs(freq)
    elif not reconstruction_mode == 'positive':
        raise ValueError('reconstruction_mode must be either "positive" or "all"')

    # Creates bandpass filter mask
    if lower is None:
        filter_mask = (freq < upper)
    elif upper is None:
        filter_mask = (freq > lower)
    else:
        filter_mask = ((freq < upper) & (freq > lower))

    X_filtered = X * filter_mask
    y_filtered = fft.ifft(X_filtered).real

    return y_filtered


"""
Function that applies a bandpass filter over a signal y.
Uses butterworth filter method. You will have to specify the sampling frequency in Hz.
If you only want a lowpass filter or highpass filter, adjust the btype argument.
"""


def frequency_filtering_butterworth(y: ndarray | list | Series,
                                    fs: float | int,
                                    order: int = 4,
                                    btype: 'str' = 'bandpass',
                                    upper: float | int | None = None,
                                    lower: float | int | None = None) -> ndarray:
    if type(y) is not Series:
        y = Series(y)

    if btype == 'bandpass' or btype == 'bandstop':
        bw_filter = butter(order, Wn=[lower, upper], btype=btype, fs=fs, output='ba')
    elif btype == 'lowpass':
        bw_filter = butter(order, Wn=upper, btype=btype, fs=fs, output='ba')
    elif btype == 'highpass':
        bw_filter = butter(order, Wn=lower, btype=btype, fs=fs, output='ba')
    else:
        raise KeyError(f'Btype must be either "bandpass" or "bandstop" or "lowpass" or "highpass"')
    filtered = filtfilt(*bw_filter, y.values)
    return filtered

# Function to plot the frequency power / frequency graph of a signal
def show_fourier_power_distribution(y: ndarray,
                                    t: ndarray,
                                    ax: [None, axes] = None,
                                    label: [None, str] = None) -> None:
    """
    Function that shows the power distribution in fourier space of a given input signal y with time axis t
    :param y: array like - time domain signal which is to be filtered
    :param t: array like - timestamps of y in seconds - timestamps do not have to be equidistant
    :param ax: matplotlib axis used to plot the fourier power distribution to
    :param label: label used for the legend of the plot
    :return:
    """
    t = array(t - min(t))  # Setting time-series to start at zero

    # Performing the FFT on the resampled signal
    N = len(y)
    X = fft.fft(y, N)  # FFT of signal Y
    X_pwr = abs(X * conj(X) / N)

    # Returns frequencies in Hz -> Note the term (1/mean(diff(t))) accounts for the sampling frequency of y
    freq = fft.fftfreq(N) * (1 / mean(diff(t)))
    mask = freq > 0  # Removes all frequencies below zero

    # Plotting the results
    if ax is None:
        _, ax = subplots(nrows=1, ncols=1, figsize=(10, 2), tight_layout=True)
    ax.set_title(f'FFT analysis: Power vs. frequency \n'
                 f'Max / min frequency: {max(abs(freq)):.2f}Hz / {min(abs(freq)):.2f}Hz \n'
                 f'Sampling freq. of {mean(1 / diff(t)):.2f}Hz \n'
                 f'Max power at {freq[mask][argmax(X_pwr[mask])]:.2f}Hz')

    if label is None:
        label = ''
    ax.plot(freq[mask], X_pwr[mask], c='b', label=label)
    ax.set_ylabel('PWR')
    ax.set_xlabel('Frequency [Hz]')
    ax.legend(loc='best')

def plot_psd(y: ndarray | Series | list,
             t: ndarray | Series | list,
             ax: [None, axes] = None,
             label: [None, str] = None) -> None:
    """
    Function that shows the power distribution in fourier space of a given input signal y with time axis t
    :param y: array like - time domain signal which is to be filtered
    :param t: array like - timestamps of y in seconds - timestamps do not have to be equidistant
    :param ax: matplotlib axis used to plot the fourier power distribution to
    :param label: label used for the legend of the plot
    :return:
    """
    if len(y) != len(t):
        raise ValueError('Make sure that y and t have the same length')

    if type(y) is not Series:
        y = Series(y)
    if type(t) is not Series:
        t = Series(t)

    t = t-t[0]
    avg_sampling_frequency = t.diff().mean()

    f, Pxx = welch(y, avg_sampling_frequency)



# Function to find R peaks in signal energy
def get_peaks(y: Series | ndarray | list,
              quant: float = 0.8,
              output: str = 'all',
              **kwargs) -> tuple[ndarray, dict] | ndarray:
    """
    Find peaks in time series
    :param y: Array-like: Signal time series
    :param quant: Defines the minimum height of the peaks
    :param output: Defines the type of output to be returned
    :param kwargs: Keyword arguments passed to scipy.signal.find_peaks
    :return: tuple with peak locations and values
    """

    height = quantile(y, quant)
    peaks = find_peaks(y, height=height, **kwargs)

    if output == 'locs':
        return peaks[0]
    else:
        return peaks


def peak_correction(seeds: ndarray[int, int_] | list[int, int_],
                    raw_signal: ndarray | Series | list,
                    window: int = 6) -> list:
    """
    Method that finds local maximum around a seed point in a raw signal
    :param raw_signal: array-like signal in which local maximum is to be found
    :param seeds: array-like. Seed locations in which vicinity the maximums are found. Contains indices
    :param window:
    :return:
    """
    try:
        if type(raw_signal) is not Series:
            raw_signal = Series(raw_signal)
    except TypeError:
        raise TypeError('raw_signal must be pd.Series, ndarray or list')
    new_peaks = []
    for num, seed in enumerate(seeds):
        if not isinstance(seed, (int, integer)):
            raise ValueError(f'All seeds elements must be an integer. Element {num} is of type {type(seed)}')
        if raw_signal[seed - window:seed + window].empty:
            continue
        if seed < window - 1:
            new_peaks.append(raw_signal[0:window - 1].idxmax())
        else:
            new_peaks.append(raw_signal[seed - window:seed + window].idxmax())
    return new_peaks


# Method to return unit vector of the input
def unit_vector(vector: ndarray) -> ndarray:
    """
    Return Unit Vector of Input
    :param vector: array-like    
    :return:  normalized (with norm(vector) = 1)
    """
    return vector / linalg.norm(vector)


# Returns vector with mean 0
def zero_mean_vector(vector: ndarray) -> ndarray:
    """
    Return Zero Mean Vector
    :param vector: array-like
    :return: array-like with mean zero
    """
    return vector - mean(vector)


# Applies a gaussian averaging filter to a vector
def symmetric_gaussian_moving_average(y: ndarray, L: int = 10, std: float = 1.1) -> ndarray:
    """
    Symmetric averaging filter with a gaussian window.
    :param y: Array-like signal to be filtered
    :param L: Int size of averaging window
    :param std: Standard deviation of Gaussian distribution
    :return: Array-like average signal after filtering
    """

    if L % 2 == 0:
        L += 1
    window: ndarray = windows.gaussian(M=L, std=std, sym=True)
    return convolve(y, window / window.sum(), 'same')


# Applies an exponential averaging filter to a vector
def symmetric_exponential_moving_average(y: ndarray, L: int = 10, tau: float = 1.1) -> ndarray:
    """
    Symmetric averaging filter with an exponential window.
    :param y: Array-like signal to be filtered
    :param L: Int size of averaging window
    :param tau: Decay of exponential window
    :return: Array-like average signal after filtering
    """

    if L % 2 == 0:
        L += 1
    window: ndarray = windows.exponential(L, tau=tau, sym=True)
    return convolve(y, window / sum(window), 'same')

# Function to convert timestamps to intervals
def get_pulse_metrics(timestamps: ndarray | Series, indices: ndarray | None = None) -> pd.DataFrame:
    """
    Converts timestamps in seconds to bpm
    :param timestamps: Array-like. Timestamps in seconds
    :param indices: Array-like. Indices of timestamps in original data. Not needed if timestamps is pandas Series
    :return: timestamp intervals, interval variability with
    """
    if type(timestamps) is ndarray and indices is None:
        raise ValueError('Indicate indices when passing timestamps as an ndarray.')
    elif type(timestamps) is ndarray:
        timestamps = Series(timestamps, index=indices, name='timestamps [s]')

    intervals = timestamps.diff().rename('intervals [s]')
    variability = intervals.diff().copy().rename('variability [ms]')
    diffs = variability.copy() * 1000  # Convert to milliseconds
    N = 3
    for i in range(len(variability)):
        X = diffs[i - N:i + 1] ** 2
        variability[variability.index[i]] = sqrt(mean(X))

    return pd.DataFrame({timestamps.name: timestamps,
                         intervals.name: intervals.bfill(),
                         variability.name: variability.bfill()})

def get_anomalies_from_rri(rri: list | ndarray | Series, indices: ndarray | list | None = None, **kwargs) -> list:
    """
    Method to obtain premature atrial contractions from a list of rr-intervals
    :param rri: Array-like list of rr intervals. Can also be normalized or filtered, as long as properties remain
    :param indices: Index list of where RRis are found in original signal
    :return:
    """

    if type(rri) in [list, ndarray]:
        if indices is None:
            raise ValueError('Indicate indices when passing rri as an ndarray of list.')
        rri = Series(rri, index=indices)

    # We use a small baseline filter here to obtain a vector that revolves around the 0-line
    rri.fillna(0)
    rri_f = rri - symmetric_exponential_moving_average(rri, L=6, tau=4)
    rri_f_d = rri_f.diff().fillna(0)
    rri_f_d_n = rri_f_d / (rri_f_d.abs().max())

    drop_threshold = -0.15
    rise_threshold = 0.25

    if 'rise_threshold' in kwargs:
        rise_threshold = kwargs['rise_threshold']
    if 'drop_threshold' in kwargs:
        drop_threshold = kwargs['drop_threshold']

    pac = []
    for i in range(len(rri_f_d_n) - 1):
        if rri_f_d_n.iloc[i] <= drop_threshold and rri_f_d_n.iloc[i + 1] >= rise_threshold:
            pac.append(i)
    return rri.index.values[pac]
