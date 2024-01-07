from ..DPO7254DataAcquisition import DPO7254Visa
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks


class Scope:
    def __init__(self, channels: dict, scope_ip='132.77.54.241'):
        self.device = DPO7254Visa(ip=scope_ip)
        self.channels = channels
        self.transmission_0 = None
        self.reflection_0 = None
        self.rubidium_lines = None
        self.time_axis = None

    @property
    def num_data_points(self):
        return

    def read_scope_data(self):
        self.device.acquireData(chns=self.channels.values)
        transmission = np.array(self.device.wvfm[self.channels["transmission"]])
        reflection = np.array(self.device.wvfm[self.channels["reflection"]])
        rubidium_lines = np.array(self.device.wvfm[self.channels["rubidium"]])
        return transmission, reflection, rubidium_lines

    def set_transmission_0(self):
        self.transmission_0, _, _ = self.read_scope_data()

    def set_reflection_0(self):
        _, self.reflection_0, _ = self.read_scope_data()

    def calibrate_time_axis(self):
        peaks, prop = find_peaks(self.rubidium_lines, prominence=0.017, distance=1000)  # width=50, rel_height=0.5)
        plt.figure()
        plt.plot(self.rubidium_lines)
        plt.plot(peaks, self.rubidium_lines[peaks], "x")
        idx_to_freq = (156.947e6 / 2) / (peaks[-1] - peaks[-2])
        self.time_axis = np.arange(len(self.rubidium_lines)) * idx_to_freq  # Calibration
        plt.show()

