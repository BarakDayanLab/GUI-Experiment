import numpy as np
from scipy.optimize import minimize
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RubidiumLines:
    data: np.ndarray = None
    peaks_idx: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    peaks_time: np.ndarray = None

    @property
    def num_points(self):
        return len(self.data)

    @property
    def num_peaks(self):
        return len(self.peaks_idx)

    def idx_to_freq_factor(self):
        return (156.947 / 2) / (self.peaks_idx[-1] - self.peaks_idx[-2])

    def time_to_freq_factor(self):
        return (156.947 / 2) / (self.peaks_time[-1] - self.peaks_time[-2])


class Cavity:
    def __init__(self, main_parameter: str, fit_parameters: list, bounds):
        self.main_parameter = main_parameter

        self.base_fit_parameters = ["x_0", "y_0", "m", "b"]
        self.fit_parameters = fit_parameters + self.base_fit_parameters

        self.transmission_spectrum: Optional[np.ndarray] = None
        self.reflection_spectrum: Optional[np.ndarray] = None

        self.x_0 = 1
        self.y_0 = 0.5
        self.m = 0
        self.b = 0

        self.base_bounds = [(-np.inf, -np.inf, -np.inf, -np.inf), (np.inf, np.inf, np.inf, np.inf)]
        self.bounds = [bounds[0] + self.base_bounds[0], bounds[1] + self.base_bounds[1]]

    @property
    def current_fit_value(self):
        return getattr(self, self.main_parameter)

    @property
    def num_points(self):
        return len(self.transmission_spectrum)

    @property
    def minimum_of_fit(self):
        res = minimize(self.transmission_spectrum_func, np.array([self.x_0]))
        return res.x[0]

    def linear_factor(self, x_detuning):
        return self.m * x_detuning + self.b

    def transmission_spectrum_func(self, x_detuning):
        return

    def reflection_spectrum_func(self, x_detuning):
        pass

    def fit(self, x_detuning, *args):
        self.set_fit_parameters(*args)
        return self.transmission_spectrum_func(x_detuning)

    def set_fit_parameters(self, *args):
        for idx, key in enumerate(self.fit_parameters):
            setattr(self, key, args[idx])

    def get_fit_parameters(self):
        return [getattr(self, key) for key in self.fit_parameters]


class CavityKex(Cavity):
    def __init__(self, k_i: float, h: float):
        bounds = [(0, ), (np.inf, )]
        super().__init__("k_ex", ["k_ex"], bounds)
        self.k_i = k_i
        self.h = h
        self.k_ex = 30

    def transmission_spectrum_func(self, x_detuning):
        k_total = self.k_ex + self.k_i
        k_with_detuning = k_total + 1j * (x_detuning - self.x_0)
        return self.linear_factor(x_detuning) * np.abs(1 - 2 * self.k_ex * k_with_detuning / (k_with_detuning ** 2 + self.h ** 2)) ** 2 + self.y_0

    def reflection_spectrum_func(self, x_detuning):
        k_total = self.k_ex + self.k_i
        k_with_detuning = k_total + 1j * (x_detuning - self.x_0)
        return np.abs(2 * self.k_ex * self.h / (k_with_detuning ** 2 + self.h ** 2)) ** 2 + self.y_0


class CavityFwhm(Cavity):
    def __init__(self):
        bounds = [(-np.inf, 0), (np.inf, np.inf)]
        super().__init__("fwhm", ["amp", "fwhm"], bounds)
        self.fwhm = 50
        self.amp = 1

    def transmission_spectrum_func(self, x_detuning):
        return self.linear_factor(x_detuning) * (0.5 * self.fwhm *
                                                 self.amp) / (np.pi * ((x_detuning - self.x_0) ** 2 + (0.5 * self.fwhm) ** 2)) + self.y_0
