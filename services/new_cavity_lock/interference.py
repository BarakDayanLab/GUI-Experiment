import numpy as np
from scipy.signal import butter, filtfilt
from scipy.signal import find_peaks


class InterferenceFit:
    def __init__(self, avg_num: int):
        self.avg_num = avg_num
        self.peak_idx = 0
        self.num_points = 0
        self.prev_data = None
        self.initialized = False
        self.avg_idx = 0
        self.data = None
        self.undetected_peaks = 0

    def calculate_peak_idx(self, data):
        if not self.initialized:
            self.num_points = len(data)
            self.prev_data = np.zeros((self.avg_num, self.num_points))
            self.initialized = True

        # self.data = np.abs(data - data.mean())
        # self.prev_data = np.roll(self.prev_data, 1, axis=0)
        # self.prev_data[0] = self.data
        # self.peak_idx = np.argmax(np.mean(self.prev_data, axis=0))
        self.normalize_data(data)
        peak_idx, _ = find_peaks(data, prominence=0.7)
        if len(peak_idx) != 1 and self.undetected_peaks < 6:
            self.undetected_peaks += 1
        else:
            self.undetected_peaks = 0
            self.peak_idx = peak_idx[0]

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

