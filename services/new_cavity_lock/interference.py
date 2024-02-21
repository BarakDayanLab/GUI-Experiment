import numpy as np
from scipy.signal import butter, filtfilt


class InterferenceFit:
    def __init__(self, avg_num: int):
        self.avg_num = avg_num
        self.peak_idx = 0
        self.num_points = 0
        self.prev_data = None
        self.initialized = False
        self.avg_idx = 0
        self.data = None

    def calculate_peak_idx(self, data):
        if not self.initialized:
            self.num_points = len(data)
            self.prev_data = np.zeros((self.avg_num, self.num_points))
            self.initialized = True

        self.data = np.abs(data - data.mean())
        self.prev_data = np.roll(self.prev_data, 1, axis=0)
        self.prev_data[0] = self.data
        self.peak_idx = np.argmax(np.mean(self.prev_data, axis=0))

    def enhance_peaks(self, data):
        cutoff = 1
        # noinspection PyTupleAssignmentBalance
        b, a = butter(2, cutoff, btype='low', analog=False)
        filtered_data = filtfilt(b, a, data)

        second_derivative = -np.pad(np.diff(np.diff(filtered_data)), 1)
        second_derivative -= np.min(second_derivative)
        second_derivative /= np.max(second_derivative)
        return second_derivative

