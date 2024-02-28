import functools
import numpy as np
from threading import Timer


class SetInterval(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def use_lock(lock_str="lock"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_str)
            lock.acquire()
            result = func(self, *args, **kwargs)
            lock.release()
            return result
        return wrapper
    return decorator


def transmission_spectrum(detuning, k_ex, k_i, h):
    k_total = k_ex + k_i
    k_with_detuning = k_total + 1j * detuning
    spectrum = np.abs(1 - 2 * k_ex * k_with_detuning / (k_with_detuning ** 2 + h ** 2)) ** 2
    return spectrum


def reflection_spectrum(detuning, k_ex, k_i, h):
    k_total = k_ex + k_i
    k_with_detuning = k_total + 1j * detuning
    spectrum = np.abs(2 * k_ex * h / (k_with_detuning ** 2 + h ** 2)) ** 2
    return spectrum


def lorentzian_spectrum(detuning, fwhm, amp):
    spectrum = 0.5 * fwhm * amp / (np.pi * (detuning ** 2 + (0.5 * fwhm) ** 2))
    return spectrum

