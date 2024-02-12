import numpy as np


class InterferenceFit:
    def __init__(self):
        self.avg_num = 10
        self.peak_idx = 0
        self.num_points = 0
        self.prev_data = None
        self.initialized = False
        self.avg_idx = 0

    def get_peak_idx(self, data):
        if not self.initialized:
            self.num_points = len(data)
            self.prev_data = np.zeros((self.avg_num, self.num_points))
            self.initialized = True

        self.prev_data = np.roll(self.prev_data, 1, axis=0)
        self.prev_data[0] = data
        self.peak_idx = np.argmax(np.mean(self.prev_data, axis=0))

