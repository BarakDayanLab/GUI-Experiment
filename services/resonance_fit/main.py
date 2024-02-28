from services.new_cavity_lock.model.data_loader import ScopeDataLoader
from cavity import CavityFwhm
from services.resonance_fit.view import App
from services.resonance_fit.resonance_fit import ResonanceFit
import numpy as np
from scipy.fft import rfft
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

def preprocess_data(data):
    # data = np.convolve(data, np.ones(int(1e2)), mode='valid')
    orig_data = data.copy()
    orig_data -= np.min(orig_data)
    orig_data /= np.max(orig_data)

    fft_data = rfft(data)
    # fft_data = np.abs(fft_data)**2

    normal_cutoff = 2 / 500
    # Get the filter coefficients
    b, a = butter(6, normal_cutoff, btype='low', analog=False)
    filtered_data = filtfilt(b, a, data)
    # return y

    # filtered_data = irfft(fft_data * data_filter)

    second_der = -np.diff(np.diff(filtered_data))
    second_der -= np.min(second_der)
    second_der /= np.max(second_der)
    # for i in range(30):
    #     data = np.convolve(data, np.ones(int(1e2)), mode='same')
    filtered_data -= np.min(filtered_data)
    filtered_data /= np.max(filtered_data)

    return orig_data, filtered_data, second_der

if __name__ == '__main__':
    data_loader = ScopeDataLoader(channels_dict={"transmission": 1, "rubidium": 3}, scope_ip=None)
    # data_loader = DataLoaderRedPitaya()
    cavity = CavityFwhm()
    model = ResonanceFit(cavity)
    app = App(cavity, data_loader)
    app.mainloop()

    # a = fftshift(np.pad(np.ones(100), 450))
    # b = np.pad(np.ones(100), 450)
    # c = np.ones(100)
    # x = np.linspace(-np.pi, np.pi, 1000)
    # f = np.sin(x)
    # plt.plot(x, irfft(rfft(f)*rfft(a)))
    # plt.plot(x, irfft(rfft(f)*rfft(b)))
    # plt.plot(x, irfft(rfft(f)*rfft(c, n=1000)))
    # plt.show()
    data_loader.start()
    # plt.ion()
    # while True:
    data = data_loader.queue.get()
    # model.fit_data(*data)
    data, fft_data, der = preprocess_data(data[0])
    plt.plot(fft_data)
    plt.plot(der)
    # plt.show()
