import numpy as np
from scipy.signal import butter, filtfilt
from scipy.signal import find_peaks


class InterferenceFit:
    def __init__(self):
        self.peak_idx = 0
        self.undetected_peaks = 0
        self.data = None

    def calculate_peak_idx(self, data):
        self.data = np.abs(data - data.mean())

        self.data = self.normalize_data(self.data)
        self.data = self.enhance_peaks(self.data)
        if self.data.std() > 0.1:
            return

        self.peak_idx = np.argmax(self.data)

    @staticmethod
    def normalize_data(data):
        data -= data.min()
        data /= data.max()
        return data

    @staticmethod
    def enhance_peaks(data):
        second_derivative = -np.pad(np.diff(np.diff(data)), 1)
        second_derivative -= np.min(second_derivative)
        second_derivative /= np.max(second_derivative)
        return second_derivative

