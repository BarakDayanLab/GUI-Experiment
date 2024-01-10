from ..DPO7254DataAcquisition import DPO7254Visa
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit


class ResonanceFit:
    def __init__(self, channels_dict: dict, scope_ip='132.77.54.241', live=True):
        self.scope = DPO7254Visa(ip=scope_ip)
        self.channels_dict = channels_dict
        self.x_axis = None

        self.transmission_0 = 0
        self.transmission_100 = 0
        self.current_transmission_spectrum = None
        self.current_reflection_spectrum = None

        self.rubidium_lines = None
        self.rubidium_peaks = None

        self.optimal_parameters = None

    def calibrate_x_axis(self):
        self.rubidium_lines = self.read_scope_data("rubidium")
        self.rubidium_peaks, _ = find_peaks(self.rubidium_lines, prominence=0.017, distance=1000)  # width=50, rel_height=0.5)
        idx_to_freq = (156.947e6 / 2) / (self.rubidium_peaks[-1] - self.rubidium_peaks[-2])
        x_axis = np.arange(len(self.rubidium_lines)) * idx_to_freq  # Calibration

        self.x_axis = x_axis

    def read_scope_data(self, channel):
        channel_number = self.channels_dict[channel]
        self.scope.acquireData(chns=channel_number)
        data = np.array(self.scope.wvfm[channel_number])
        return data

    def set_transmission_0(self):
        self.transmission_0 = self.read_scope_data("transmission")

    def set_transmission_100(self):
        self.transmission_100 = self.read_scope_data("transmission")

    @staticmethod
    def transmission_spectrum(x_detuning, k_ex, k_i, h, x_0):
        k_total = k_ex + k_i
        k_with_detuning = k_total + 1j * (x_detuning - x_0)
        return np.abs(1 - 2*k_ex*k_with_detuning/(k_with_detuning ** 2 + h ** 2)) ** 2

    @staticmethod
    def reflection_spectrum(x_detuning, k_ex, k_i, h, x_0):
        k_total = k_ex + k_i
        k_with_detuning = k_total + 1j * (x_detuning - x_0)
        return np.abs(2 * k_ex * h / (k_with_detuning ** 2 + h ** 2)) ** 2

    @staticmethod
    def stacked_spectrum(x_detuning, k_ex, k_i, h, x_0):
        return np.hstack((ResonanceFit.transmission_spectrum(x_detuning, k_ex, k_i, h, x_0),
                          ResonanceFit.reflection_spectrum(x_detuning, k_ex, k_i, h, x_0)))

    def read_transmission_spectrum(self):
        current_transmission = self.read_scope_data("transmission")
        transmission_norm_factor = 1 / (self.transmission_100 - self.transmission_0)
        self.current_transmission_spectrum = transmission_norm_factor * (current_transmission - self.transmission_0)

    def read_reflection_spectrum(self):
        current_reflection = self.read_scope_data("reflection")
        reflection_norm_factor = 1 / (self.transmission_100 - self.transmission_0)
        self.current_reflection_spectrum = reflection_norm_factor * (current_reflection - self.transmission_0)

    def fit_current_spectrum(self):
        y_data = np.hstack((self.current_transmission_spectrum, self.current_reflection_spectrum))
        self.optimal_parameters, _ = curve_fit(self.stacked_spectrum, self.x_axis, y_data)

    def plot_spectrum_fit(self):
        plt.plot(self.x_axis, self.current_transmission_spectrum)
        plt.plot(self.x_axis, self.current_reflection_spectrum)
        plt.plot(self.x_axis, self.transmission_spectrum(self.x_axis, *self.optimal_parameters))
        plt.plot(self.x_axis, self.reflection_spectrum(self.x_axis, *self.optimal_parameters))
        plt.show()

# class Scope:
#     def __init__(self, x_axis, channels_dict):
#         self.x_axis = x_axis
#         self.channels_dict = channels_dict
#
#         n_data_points = len(x_axis)
#         self.default_spectrum = {
#             "transmission": np.ones(n_data_points),
#             "reflection": np.zeros(n_data_points),
#             "rubidium": np.zeros(n_data_points)
#         }
#
#         wvfm = {1: 1}
#
#     def acquireData(self, chns):
#         pass



if __name__ == '__main__':
    transmission_channel = input("Enter the transmission signal channel: ")
    reflection_channel = input("Enter the reflection signal channel: ")
    rubidium_channel = input("Enter the rubidium channel: ")
    resonance_fit = ResonanceFit({"transmission": transmission_channel,
                          "reflection": reflection_channel,
                          "rubidium": rubidium_channel})

    input("Scan to find the rubidium lines, then press Enter")
    resonance_fit.calibrate_x_axis()

    plt.figure()
    plt.plot(resonance_fit.rubidium_lines)
    plt.plot(resonance_fit.rubidium_peaks, resonance_fit.rubidium_lines[resonance_fit.rubidium_peaks], "x")
    plt.show()

    input("Set reflection and transmission signal to 0, then press Enter")
    resonance_fit.set_transmission_0()
    input("Turn on the transmission signal (without the resonance), then press Enter")
    resonance_fit.set_transmission_100()
    input("Bring the resonance back")
    resonance_fit.read_transmission_spectrum()

    input("Turn the transmission off, and the reflection on, then press Enter")
    resonance_fit.read_reflection_spectrum()

    resonance_fit.fit_current_spectrum()
    resonance_fit.plot_spectrum_fit()
