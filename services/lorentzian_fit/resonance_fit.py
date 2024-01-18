import sys
import time
import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, convolve, find_peaks_cwt
from scipy.optimize import curve_fit

plt.ion()


class ResonanceFit:
    def __init__(self, k_i=3.9, h=0.6, rolling_avg=100, prominence=0.03, wlen=2300, distance=500):
        self.k_i = k_i
        self.h = h
        self.rolling_avg = rolling_avg
        self.prominence = prominence
        self.wlen = wlen
        self.distance = distance

        self.k_ex = 0
        self.x_0 = 0
        self.y_0 = 0
        self.x_0_idx = 0

        self.current_rubidium_lines = None
        self.current_transmission = None
        self.current_rubidium_peaks = None
        self.freq_axis = None

        self.num_unsuccessful_fits = 0
        self.resonance_area = None

        format = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
        handler = logging.FileHandler("resonance_fit.log")
        handler.setLevel(logging.WARNING)
        handler.setFormatter(format)
        self.logger = logging.getLogger("resonance_fit_logger")
        self.logger.addHandler(handler)

    def normalize_data(self, data):
        data -= data.min()
        data /= data.max()

        data = np.convolve(data, np.ones(self.rolling_avg) / self.rolling_avg, mode='valid')
        return data

    def get_current_data(self):
        return [self.current_rubidium_lines, self.current_transmission]

    def calibrate_freq_axis(self, rubidium_lines):
        self.current_rubidium_lines = self.normalize_data(rubidium_lines)
        self.current_rubidium_peaks, _ = find_peaks(self.current_rubidium_lines, prominence=self.prominence, wlen=self.wlen,
                                                    distance=self.distance)

        idx_to_freq = (156.947 / 2) / (self.current_rubidium_peaks[-1] - self.current_rubidium_peaks[-2])
        freq_axis = np.arange(len(self.current_rubidium_lines)) * idx_to_freq  # Calibration
        self.freq_axis = freq_axis

    @staticmethod
    def transmission_spectrum(x_detuning, k_ex, k_i, h, x_0, y_0):
        k_total = k_ex + k_i
        k_with_detuning = k_total + 1j * (x_detuning - x_0)
        return np.abs(1 - 2 * k_ex * k_with_detuning / (k_with_detuning ** 2 + h ** 2)) ** 2 + y_0

    @staticmethod
    def reflection_spectrum(x_detuning, k_ex, k_i, h, x_0, y_0):
        k_total = k_ex + k_i
        k_with_detuning = k_total + 1j * (x_detuning - x_0)
        return np.abs(2 * k_ex * h / (k_with_detuning ** 2 + h ** 2)) ** 2 + y_0

    def transmission_spectrum_without_cavity_params(self, x_detuning, k_ex, y_0):
        return self.transmission_spectrum(x_detuning, k_ex, self.k_i, self.h, self.x_0, y_0)

    def transmission_spectrum_k_ex(self, x_detuning, k_ex):
        return self.transmission_spectrum(x_detuning, k_ex, self.k_i, self.h, self.current_x_0, self.y_0)

    def calculate_resonance_area(self):
        self.resonance_area = (self.x_0 - 200 < self.freq_axis) * (self.freq_axis < self.x_0 + 200)

    def fit_transmission_spectrum(self, transmission_spectrum):
        self.current_transmission = self.normalize_data(transmission_spectrum)
        self.x_0_idx = self.current_transmission.argmin()
        self.x_0 = self.freq_axis[self.x_0_idx]
        self.calculate_resonance_area()
        # noinspection PyTupleAssignmentBalance
        optimal_parameters, _ = curve_fit(self.transmission_spectrum_without_cavity_params,
                                          self.freq_axis[self.resonance_area],
                                          self.current_transmission[self.resonance_area],
                                          p0=[30, 1])
        self.k_ex, self.y_0 = optimal_parameters

    def get_rubidium_peaks(self):
        peaks = np.vstack((self.freq_axis[self.current_rubidium_peaks],
                           self.current_rubidium_lines[self.current_rubidium_peaks])).T
        return peaks.T

    def get_x0_coords(self):
        return np.array([self.x_0, self.current_transmission[self.x_0_idx]])
