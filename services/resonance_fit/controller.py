import numpy as np
import matplotlib.pyplot as plt
from pynput.keyboard import GlobalHotKeys
from threading import Thread
import time


class ResonanceFitController:
    def __init__(self, app, model, data_loader):
        self.app = app
        self.model = model
        self.data_loader = data_loader

        hotkeys = {"<ctrl>+p": self.toggle_pause,
                   "<ctrl>+q": self.stop,}
        self.keyboard_listener = GlobalHotKeys(hotkeys)
        self.keyboard_listener.start()

        self.pause = False
        self.stop = False

        self.data_loader.start()
        rubidium_lines = self.data_loader.queue.get()[0]
        self.model.set_x_axis(rubidium_lines)

        self.thread = Thread(target=self.on_data)
        self.thread.start()

    # ------------------ KEYBOARD INTERRUPTS ------------------ #
    def toggle_pause(self):
        self.pause = not self.pause

    def stop(self):
        self.stop = True
        self.thread.join()
        self.data_loader.stop()
        self.app.destroy()

    def wait(self):
        while self.pause:
            plt.pause(0.1)

    # ------------------ GUI ------------------ #

    def calibrate_peaks_params(self):
        rubidium_lines = self.data_loader.queue.get()[0]
        points = self.app.show_calibration_window(rubidium_lines)
        num_idx_in_peak = np.round(np.abs(points[0][0] - points[1][0]))
        self.model.calibrate_peaks_params(num_idx_in_peak)
        self.model.set_x_axis(rubidium_lines)

    def select_peak(self, point):
        distances = np.sum((self.model.rubidium_peaks - point) ** 2, axis=1)
        self.model.lock_idx = np.argmin(distances)

    # ------------------ RUN ------------------ #

    def update_app_queue(self, data):
        if self.app.queue.full():
            self.app.queue.get()
        self.app.queue.put(data)

    def on_data(self):
        while not self.stop:
            if self.pause:
                time.sleep(0.1)
                continue

            data = self.data_loader.queue.get()
            success = self.model.fit_data(*data)
            rubidium_lines = self.model.rubidium_lines.data
            transmission_spectrum = self.model.cavity.transmission_spectrum

            data = (self.model.x_axis, rubidium_lines, transmission_spectrum)
            fit = None
            if success:
                title = (f"Lock Error: {self.model.lock_error:.2f} MHz, "
                         f"{self.model.cavity.main_parameter}: {self.model.cavity.current_fit_value:.2f}")
                fit = (self.model.relevant_x_axis, self.model.rubidium_peaks,
                       self.model.selected_peak, self.model.lorentzian_center,
                       self.model.transmission_fit, title)

            self.update_app_queue((data, fit))

    # ------------------ SAVE DATA ------------------ #

    # def get_save_paths(self):
    #     date = time.strftime("%Y%m%d")
    #     hours = time.strftime("%H%M%S")
    #
    #     transmission_filename = f"{date}-{hours}_cavity_spectrum.npy"
    #     transmission_path = os.path.join(self.save_folder, date, transmission_filename)
    #
    #     rubidium_filename = f"{date}-{hours}_rubidium_spectrum.npy"
    #     rubidium_path = os.path.join(self.save_folder, date, rubidium_filename)
    #     return transmission_path, rubidium_path
    #
    # def save_spectrum(self):
    #     if self.save_folder is None:
    #         return
    #
    #     now = time.time()
    #     time_since_last_save = now - self.last_save_time
    #     if time_since_last_save >= self.save_time:
    #         transmission_path, rubidium_path = self.get_save_paths()
    #         np.save(transmission_path, self.cavity.transmission_spectrum)
    #         np.save(rubidium_path, self.rubidium_lines.data)
    #         self.last_save_time = now
