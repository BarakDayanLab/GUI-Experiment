import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from .cavity import RubidiumLines
from scipy.signal import butter, filtfilt


class ResonanceFit:
    def __init__(self, cavity):
        self.cavity = cavity
        self.rubidium_lines = RubidiumLines()

        self.lock_idx = 4
        self.lock_offset = 0

        self.x_axis = np.array([])
        self.current_relevant_area = None
        self.relevant_x_axis = None

        self.fit_params_history = np.empty((0, len(self.cavity.fit_parameters) + 1))

        self.prominence = 0.15
        self.frequency_cutoff = 2 / 1000
        self.w_len = 934
        self.distance = 84

    @property
    def lock_error(self):
        return self.cavity.x_0 - self.x_axis[self.rubidium_lines.peaks_idx[self.lock_idx]] + self.lock_offset

    @property
    def rubidium_peaks(self):
        x_vals = self.x_axis[self.rubidium_lines.peaks_idx]
        y_vals = self.rubidium_lines.data[self.rubidium_lines.peaks_idx]
        peaks = np.vstack([x_vals, y_vals]).T
        return peaks

    @property
    def selected_peak(self):
        return self.rubidium_peaks[self.lock_idx]

    @property
    def transmission_fit(self):
        return self.cavity.transmission_spectrum_func(self.relevant_x_axis)

    @property
    def lorentzian_center(self):
        return np.array([self.cavity.x_0, self.cavity.transmission_spectrum_func(self.cavity.x_0)])

    # ------------------ CALIBRATIONS ------------------ #

    def set_x_axis(self, rubidium_lines):
        rubidium_lines = self.normalize_data(rubidium_lines)
        self.x_axis = np.arange(len(rubidium_lines))

    def calibrate_peaks_params(self, num_idx_in_peak):
        self.w_len = num_idx_in_peak * 1.1
        self.distance = int(num_idx_in_peak // 10)
        self.frequency_cutoff = 1 / num_idx_in_peak

    def calibrate_x_axis(self) -> bool:
        enhanced_data = self.enhance_peaks(self.rubidium_lines.data)
        self.rubidium_lines.peaks_idx, _ = find_peaks(enhanced_data, prominence=self.prominence,
                                                      wlen=self.w_len, distance=self.distance)
        if self.rubidium_lines.num_peaks != 6:
            return False
        self.x_axis = np.arange(self.rubidium_lines.num_points) * self.rubidium_lines.idx_to_freq_factor()
        return True

    def calculate_relevant_area(self):
        self.current_relevant_area = (self.cavity.x_0 - 90 < self.x_axis) * (self.x_axis < self.cavity.x_0 + 90)
        self.relevant_x_axis = self.x_axis[self.current_relevant_area]

    # ------------------ DATA PROCESSING ------------------ #
    @staticmethod
    def normalize_data(data):
        data -= np.min(data)
        data /= np.max(data)
        return data

    def enhance_peaks(self, data):
        nyquist_freq = 0.5
        cutoff = self.frequency_cutoff / nyquist_freq
        # noinspection PyTupleAssignmentBalance
        b, a = butter(2, cutoff, btype='low', analog=False)
        filtered_data = filtfilt(b, a, data)

        second_derivative = -np.pad(np.diff(np.diff(filtered_data)), 1)
        second_derivative -= np.min(second_derivative)
        second_derivative /= np.max(second_derivative)
        return second_derivative

    # ------------------ FIT ------------------ #

    @staticmethod
    def r2_score(y, f):
        y_bar = y.mean()
        ss_res = ((y - f) ** 2).sum()
        ss_tot = ((y - y_bar) ** 2).sum()
        return 1 - (ss_res / ss_tot)

    def fit_transmission_spectrum(self) -> bool:
        self.cavity.x_0 = self.x_axis[self.cavity.transmission_spectrum.argmin()]
        self.calculate_relevant_area()

        try:
            # noinspection PyTupleAssignmentBalance
            optimal_parameters, covariance = curve_fit(self.cavity.fit,
                                                       self.relevant_x_axis,
                                                       self.cavity.transmission_spectrum[self.current_relevant_area],
                                                       p0=self.cavity.get_fit_parameters(),
                                                       bounds=self.cavity.bounds)
        except Exception as err:
            print(err)
            return False

        self.cavity.set_fit_parameters(*optimal_parameters)
        score = self.r2_score(self.cavity.transmission_spectrum[self.current_relevant_area],
                              self.cavity.transmission_spectrum_func(self.relevant_x_axis))
        if score < 0.6:
            return True

        return True

    # ------------------ READ DATA ------------------ #

    def fit_data(self, rubidium_lines, transmission_spectrum):
        self.rubidium_lines.data = self.normalize_data(rubidium_lines)
        self.cavity.transmission_spectrum = self.normalize_data(transmission_spectrum)
        if len(self.x_axis) != self.rubidium_lines.num_points:
            self.x_axis = np.arange(self.rubidium_lines.num_points)

        if not self.calibrate_x_axis():
            return False
        if not self.fit_transmission_spectrum():
            return False

        params = self.cavity.get_fit_parameters() + [self.lock_error]
        self.fit_params_history = np.vstack([self.fit_params_history, params])
        return True
