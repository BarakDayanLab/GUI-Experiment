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
        peak_idx, _ = find_peaks(data, prominence=0.7)
        if len(peak_idx) != 1 and self.undetected_peaks < 6:
            self.undetected_peaks += 1
        else:
            self.undetected_peaks = 0
            self.peak_idx = 0

    @staticmethod
    def normalize_data(data):
        data -= data.min()
        data /= data.max()
        return data

    # def enhance_peaks(self, data):
    #     cutoff = 1
    #     # noinspection PyTupleAssignmentBalance
    #     b, a = butter(2, cutoff, btype='low', analog=False)
    #     filtered_data = filtfilt(b, a, data)
    #
    #     second_derivative = -np.pad(np.diff(np.diff(filtered_data)), 1)
    #     second_derivative -= np.min(second_derivative)
    #     second_derivative /= np.max(second_derivative)
    #     return second_derivative

