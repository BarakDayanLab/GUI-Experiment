import numpy as np
import matplotlib.pyplot as plt
from threading import Thread, Lock
import time


class ResonanceFitController:
    def __init__(self, app, model, data_loader):
        self.app = app
        self.model = model
        self.data_loader = data_loader

        self.lock = Lock()
        self.model_lock = Lock()
        self.stop = False

        self.data_loader.start()
        rubidium_lines = self.data_loader.queue.get()[0]
        self.model.set_x_axis(rubidium_lines)

        self.thread = Thread(target=self.on_data, daemon=True)
        self.thread.start()

    # ------------------ GUI ------------------ #

    def calibrate_peaks_params(self):
        rubidium_lines = self.data_loader.queue.get()[0]
        points = self.app.show_calibration_window(rubidium_lines)
        num_idx_in_peak = np.round(np.abs(points[0][0] - points[1][0]))

        self.model_lock.acquire()
        self.model.calibrate_peaks_params(num_idx_in_peak)
        self.model_lock.release()

    def select_peak(self, point):
        distances = np.sum((self.model.rubidium_peaks - point) ** 2, axis=1)
        self.model.lock_idx = np.argmin(distances)

    def stop(self):
        self.stop = True
        self.data_loader.stop()
        self.thread.join()

    # ------------------ RUN ------------------ #

    def update_app_queue(self, data):
        if self.app.queue.full():
            self.app.queue.get()
        self.app.queue.put(data)

    def on_data(self):
        while not self.stop:
            self.lock.acquire()
            data = self.data_loader.queue.get()

            self.model_lock.acquire()
            success = self.model.fit_data(*data)
            self.model_lock.release()

            rubidium_lines = self.model.rubidium_lines.data
            transmission_spectrum = self.model.cavity.transmission_spectrum

            data = (self.model.x_axis.copy(), rubidium_lines.copy(), transmission_spectrum.copy())
            fit = None
            if success:
                title = (f"Lock Error: {self.model.lock_error:.2f} MHz, "
                         f"{self.model.cavity.main_parameter}: {self.model.cavity.current_fit_value:.2f}")
                fit = (self.model.relevant_x_axis.copy(), self.model.rubidium_peaks.copy(),
                       self.model.selected_peak.copy(), self.model.lorentzian_center.copy(),
                       self.model.transmission_fit.copy(), title)

                self.update_app_queue((data, fit))

            self.lock.release()

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
