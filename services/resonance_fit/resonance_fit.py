import os
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from cavity import RubidiumLines, CavityFwhm, CavityKex
from pynput.keyboard import GlobalHotKeys


class BaseResonanceFit:
    pass


class ResonanceFit:
    def __init__(self, calc_k_ex=False, save_folder=None, save_time=60, show_buttons=False):
        self.cavity = CavityKex(k_i=3.9, h=0.6) if calc_k_ex else CavityFwhm()
        self.lock_idx = 4
        self.save_folder = save_folder
        self.save_time = save_time
        self.last_save_time = time.time()
        self.pause = False

        self.rubidium_lines = RubidiumLines()
        self.x_axis = None

        self.current_relevant_area = None
        self.relevant_x_axis = None

        self.fit_params_history = np.empty((0, len(self.cavity.fit_parameters)+1))

        hotkeys = {"<ctrl>+p": self.toggle_pause}
        self.keyboard_listener = GlobalHotKeys(hotkeys)
        self.keyboard_listener.start()

        self.prominence = 0.03
        self.rolling_avg = 100
        self.w_len = 2300
        self.distance = 100
        self.width = 1000

    @property
    def lock_error(self):
        return self.cavity.x_0 - self.x_axis[self.rubidium_lines.peaks_idx[self.lock_idx]] + 80

    @property
    def rubidium_peaks(self):
        x_vals = self.x_axis[self.rubidium_lines.peaks_idx]
        y_vals = self.rubidium_lines.data[self.rubidium_lines.peaks_idx]
        peaks = np.vstack([x_vals, y_vals]).T
        return peaks

    @property
    def lorentzian_center(self):
        return np.array([self.cavity.x_0, self.cavity.transmission_spectrum_func(self.cavity.x_0)])

    # ------------------ KEYBOARD INTERRUPTS ------------------ #
    def toggle_pause(self):
        self.pause = not self.pause

    def wait(self):
        while self.pause:
            plt.pause(0.1)

    # ------------------ CALIBRATIONS ------------------ #

    def calibrate_peaks_params(self, num_idx_in_peak):
        self.w_len = num_idx_in_peak * 1.1
        self.width = self.w_len // 5
        self.distance = int(num_idx_in_peak // 10)
        self.rolling_avg = int(num_idx_in_peak // 10)

    def calibrate_peaks_params_gui(self, rubidium_lines):
        self.x_axis = np.arange(len(rubidium_lines))
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(self.x_axis, rubidium_lines)
        points = fig.ginput(2, timeout=0, show_clicks=True)
        plt.close(fig)

        num_idx_in_peak = np.round(np.abs(points[0][0] - points[1][0]))
        self.calibrate_peaks_params(num_idx_in_peak)

    def calibrate_x_axis(self) -> bool:
        self.rubidium_lines.peaks_idx, _ = find_peaks(self.rubidium_lines.data, prominence=self.prominence,
                                                      wlen=self.w_len, distance=self.distance, width=self.width)
        if self.rubidium_lines.num_peaks != 6:
            return False
        self.x_axis = np.arange(self.rubidium_lines.num_points) * self.rubidium_lines.idx_to_freq_factor()
        return True

    def calculate_relevant_area(self):
        self.current_relevant_area = (self.cavity.x_0 - 90 < self.x_axis) * (self.x_axis < self.cavity.x_0 + 90)
        self.relevant_x_axis = self.x_axis[self.current_relevant_area]

    # ------------------ DATA PROCESSING ------------------ #

    def update_rubidium_lines(self, rubidium_lines):
        self.rubidium_lines.data = self.preprocess_data(rubidium_lines)

    def update_transmission_spectrum(self, transmission_spectrum):
        self.cavity.transmission_spectrum = self.preprocess_data(transmission_spectrum)

    def preprocess_data(self, data):
        data -= data.min()
        data /= data.max()
        data = np.convolve(data, np.ones(self.rolling_avg) / self.rolling_avg, mode='valid')
        return data

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
            return False

        return True

    # ------------------ SAVE DATA ------------------ #
    def get_save_paths(self):
        date = time.strftime("%Y%m%d")
        hours = time.strftime("%H%M%S")

        transmission_filename = f"{date}-{hours}_cavity_spectrum.npy"
        transmission_path = os.path.join(self.save_folder, date, transmission_filename)

        rubidium_filename = f"{date}-{hours}_rubidium_spectrum.npy"
        rubidium_path = os.path.join(self.save_folder, date, rubidium_filename)
        return transmission_path, rubidium_path

    def save_spectrum(self):
        if self.save_folder is None:
            return

        now = time.time()
        time_since_last_save = now - self.last_save_time
        if time_since_last_save >= self.save_time:
            transmission_path, rubidium_path = self.get_save_paths()
            np.save(transmission_path, self.cavity.transmission_spectrum)
            np.save(rubidium_path, self.rubidium_lines.data)
            self.last_save_time = now


class ResonanceFitGraphics:
    def __init__(self, resonance_fit: ResonanceFit, show_buttons=True):
        self.fig, self.plot_subfigure, self.buttons_subfigure = None, None, None
        self.show_buttons = show_buttons
        self.buttons = {}
        self.current_active_button = None

        self.resonance_fit = resonance_fit

        self.show_3rd_axis = False
        self.function_3rd_axis = None

    # ------------------ UI ------------------ #
    def update_active_button(self, button_name):
        self.current_active_button = button_name

    def activate_button(self):
        if self.current_active_button == "":
            return

        if self.current_active_button == "choose_line_button":
            self.choose_line()
        elif self.current_active_button == "show_lock_error_button":
            self.toggle_lock_error()
        self.current_active_button = ""

    def choose_line(self):
        prev_title = self.fig.texts[0].get_text()
        self.fig.suptitle("Choose line")

        point = plt.ginput(1, timeout=0, show_clicks=True)[0]
        distances = np.sum((self.resonance_fit.rubidium_peaks - point) ** 2, axis=1)
        self.resonance_fit.lock_idx = np.argmin(distances)

        self.fig.suptitle(prev_title)

    def toggle_lock_error(self):
        if not self.show_3rd_axis:
            self.initialize_plots()
            self.function_3rd_axis = None
        else:
            self.initialize_plots(plot_3rd_axis=("Lock error", "MHz"))
            self.function_3rd_axis = self.plot_lock_error

        self.show_3rd_axis = not self.show_3rd_axis

    # ------------------ PLOT FIT ------------------ #
    def initialize_figure(self):
        plt.ion()
        self.fig = plt.figure(figsize=(16, 9))  # add constrained_layout=True
        if self.show_buttons:
            self.plot_subfigure, self.buttons_subfigure = self.fig.subfigures(2, 1, height_ratios=[94, 6])
        else:
            self.plot_subfigure = self.fig

        self.initialize_plots()
        if self.show_buttons:
            self.buttons_axis()

    def initialize_plots(self, plot_3rd_axis=None):
        n_rows = 2 if plot_3rd_axis is None else 3
        self.plot_subfigure.clear()
        self.plot_subfigure.add_subplot(n_rows, 1, 1)
        self.plot_subfigure.add_subplot(n_rows, 1, 2, sharex=self.plot_subfigure.axes[0])
        self.plot_subfigure.axes[0].set_ylabel("Transmission")
        self.plot_subfigure.axes[1].set_ylabel("Rubidium")
        self.plot_subfigure.axes[1].set_xlabel("Frequency [MHz]")

        if plot_3rd_axis is not None:
            self.plot_subfigure.add_subplot(3, 1, 3)
            self.plot_subfigure.axes[2].set_title(plot_3rd_axis[0])
            self.plot_subfigure.axes[2].set_ylabel(plot_3rd_axis[1])

    def buttons_axis(self, size=(1, 2)):
        self.buttons_subfigure.subplots(*size)

        choose_line_button = plt.Button(self.buttons_subfigure.axes[0], 'choose line')
        self.buttons.update({"choose_line_button": choose_line_button})
        choose_line_button.on_clicked(lambda _: self.update_active_button("choose_line_button"))

        show_lock_error_button = plt.Button(self.buttons_subfigure.axes[1], 'lock error')
        self.buttons.update({"show_lock_error_button": show_lock_error_button})
        show_lock_error_button.on_clicked(lambda _: self.update_active_button("show_lock_error_button"))

    def plot_data(self):
        if self.fig is None:
            self.initialize_figure()

        self.plot_subfigure.axes[0].clear(), self.plot_subfigure.axes[1].clear()
        transmission_spectrum = self.resonance_fit.cavity.transmission_spectrum
        self.plot_subfigure.axes[0].plot(self.resonance_fit.x_axis, transmission_spectrum)
        self.plot_subfigure.axes[1].plot(self.resonance_fit.x_axis, self.resonance_fit.rubidium_lines.data)
        plt.pause(0.05)

    def plot_fit(self, title=None):
        if self.fig is None:
            self.initialize_figure()

        default_title = (f"{self.resonance_fit.cavity.main_parameter}: {self.resonance_fit.cavity.current_fit_value:.2f}, "
                         f"lock error: {self.resonance_fit.lock_error:.2f}, "
                         f"$\Delta$x: {self.resonance_fit.cavity.x_0 - self.resonance_fit.cavity.minimum_of_fit:.2f}")

        title = title or default_title
        self.fig.suptitle(title)
        self.plot_transmission_fit(self.plot_subfigure.axes[0])
        self.plot_rubidium_lines(self.plot_subfigure.axes[1])
        self.show_3rd_axis and self.plot_lock_error(self.plot_subfigure.axes[2])
        plt.pause(0.05)

    def plot_transmission_fit(self, ax):
        fit = self.resonance_fit.cavity.transmission_spectrum_func(self.resonance_fit.relevant_x_axis)
        ax.scatter(*self.resonance_fit.lorentzian_center, c='g')
        ax.plot(self.resonance_fit.relevant_x_axis, fit)

    def plot_rubidium_lines(self, ax):
        rubidium_peaks = self.resonance_fit.rubidium_peaks
        ax.scatter(*rubidium_peaks.T, c='r')
        ax.scatter(*rubidium_peaks[self.resonance_fit.lock_idx], c='g')

    def plot_lock_error(self, ax):
        ax.clear()
        ax.plot(self.resonance_fit.fit_params_history[-20:, -1])

    # _, transmission_spectrum = res_fit.read_scope_data("transmission")
    #
    # transmission = np.zeros((100, transmission_spectrum.shape[0]))
    # rubidium = np.zeros((100, transmission_spectrum.shape[0]))
    # for i in range(100):
    #     _, transmission_spectrum = res_fit.read_scope_data("transmission")
    #     _, rubidium_spectrum = res_fit.read_scope_data("rubidium")
    #     transmission[i] = transmission_spectrum
    #     rubidium[i] = rubidium_spectrum
    #     time.sleep(1.15)
    #
    # np.save("transmission.npy", transmission)
    # np.save("rubidium.npy", rubidium)
