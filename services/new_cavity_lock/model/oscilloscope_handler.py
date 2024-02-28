import numpy as np
from services.resonance_fit import ResonanceFit, CavityKex
from .interference import InterferenceFit
from .data_loader import DataLoaderRedPitaya
from threading import Event, Lock
from .utilities import use_lock


class ScopeHandler:
    def __init__(self, on_fit_callback):
        self.on_fit_callback = on_fit_callback

        self.resonance_fit_data_loader = DataLoaderRedPitaya(host="rp-ffffb4.local")
        self.resonance_fit_data_loader.on_data_callback = self.on_resonance_data
        cavity = CavityKex(k_i=0, h=0)
        self.resonance_fit = ResonanceFit(cavity)

        self.interference_data_loader = DataLoaderRedPitaya(host="rp-ffff3e.local")
        self.interference_data_loader.on_data_callback = self.on_interference_data
        self.interference_fit = InterferenceFit()

        self.started_resonance_fit_event = Event()
        self.started_interference_event = Event()
        self.resonance_fit_lock = Lock()
        self.interference_lock = Lock()

        self.last_fit_success = False

    # ------------------ GENERAL ------------------ #

    def start_scopes(self):
        self.resonance_fit_data_loader.start()
        self.interference_data_loader.start()
        self.started_resonance_fit_event.wait()
        self.started_interference_event.wait()

    def stop_scopes(self):
        self.resonance_fit_data_loader.stop()
        self.interference_data_loader.stop()

    def join_scopes(self):
        self.resonance_fit_data_loader.join()
        self.interference_data_loader.join()

    def calibrate_num_points(self, num_idx_in_peak):
        self.resonance_fit.calibrate_peaks_params(num_idx_in_peak)

    # ------------------ DATA LOADER ------------------ #

    @use_lock("interference_lock")
    def on_interference_data(self, data):
        self.interference_fit.calculate_peak_idx(data[1])

        if not self.started_interference_event.is_set():
            self.started_interference_event.set()

    @use_lock("resonance_fit_lock")
    def on_resonance_data(self, data):
        self.resonance_fit.set_data(*data.copy())
        if data[1].std() >= 6e-3:
            self.last_fit_success = self.resonance_fit.fit_data()
            if self.last_fit_success:
                if len(self.resonance_fit.fit_params_history) < 2 or \
                        np.abs(self.resonance_fit.fit_params_history[-1, -1] - self.resonance_fit.fit_params_history[
                            -2, -1]) < 5:
                    self.on_fit_callback()
        else:
            self.last_fit_success = False

        if not self.started_resonance_fit_event.is_set():
            self.started_resonance_fit_event.set()

    def set_data_loader_params(self, parameters):
        self.resonance_fit_data_loader.update(parameters)
        self.interference_data_loader.update(parameters)

    # ------------------ GET ------------------ #

    @use_lock("resonance_fit_lock")
    def get_current_fit(self):
        x_axis = self.resonance_fit.x_axis.copy()
        rubidium_lines = self.resonance_fit.rubidium_lines.data.copy()
        transmission_spectrum = self.resonance_fit.cavity.transmission_spectrum.copy()
        data = (x_axis, rubidium_lines, transmission_spectrum)

        if not self.last_fit_success:
            return data, None

        lock_error = self.resonance_fit.lock_error
        main_parameter = self.resonance_fit.cavity.main_parameter
        current_fit_value = self.resonance_fit.cavity.current_fit_value
        title = f"{main_parameter.upper()}: {current_fit_value:.2f}, Lock Error: {lock_error:.2f} MHz"

        relevant_x_axis = self.resonance_fit.relevant_x_axis.copy()
        rubidium_peaks = self.resonance_fit.rubidium_peaks.copy()
        selected_peak = self.resonance_fit.selected_peak.copy()
        lorentzian_center = self.resonance_fit.lorentzian_center.copy()
        transmission_fit = self.resonance_fit.transmission_fit.copy()

        fit = (relevant_x_axis, rubidium_peaks, selected_peak, lorentzian_center, transmission_fit, title)
        return data, fit

    @use_lock("resonance_fit_lock")
    def get_transmission_spectrum(self):
        return self.resonance_fit.cavity.transmission_spectrum.copy()

    @use_lock("resonance_fit_lock")
    def get_rubidium_lines(self):
        rubidium_lines = self.resonance_fit.rubidium_lines.data.copy()
        return rubidium_lines

    @use_lock("resonance_fit_lock")
    def get_rubidium_peaks(self):
        return self.resonance_fit.rubidium_peaks.copy()

    @use_lock("interference_lock")
    def get_interference_peak(self):
        # peak_idx = self.interference_fit.peak_idx
        # return self.resonance_fit.x_axis[peak_idx]
        return self.interference_fit.data

    @use_lock("resonance_fit_lock")
    def get_k_ex(self):
        return self.resonance_fit.cavity.k_ex

    @use_lock("resonance_fit_lock")
    def set_lock_offset(self, lock_offset):
        self.resonance_fit.lock_offset = lock_offset

    @use_lock("resonance_fit_lock")
    def get_lock_error(self):
        return self.resonance_fit.lock_error

    # ------------------ SET ------------------ #

    @use_lock("resonance_fit_lock")
    def set_lock_idx(self, lock_idx):
        self.resonance_fit.lock_idx = lock_idx

    @use_lock("resonance_fit_lock")
    def set_kappa_i(self, kappa_i):
        self.resonance_fit.cavity.k_i = kappa_i

    @use_lock("resonance_fit_lock")
    def set_h(self, h):
        self.resonance_fit.cavity.h = h
