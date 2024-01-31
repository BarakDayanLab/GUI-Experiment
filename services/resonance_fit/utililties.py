import numpy as np


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
