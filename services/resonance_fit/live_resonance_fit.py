import re
import os
import time
import numpy as np
from services.resonance_fit.scope_connection import Scope, FakeScope
from services.resonance_fit.resonance_fit import ResonanceFit, ResonanceFitGraphics


class FetchResonanceFit(ResonanceFit):
    def __init__(self, wait_time=0.1, calc_k_ex=False, save_folder=None, save_time=60, show_buttons=False):
        super().__init__(calc_k_ex=calc_k_ex, save_folder=save_folder, save_time=save_time, show_buttons=show_buttonss)
        self.wait_time = wait_time

        self.stop_condition = False

    # ------------------ READ DATA ------------------ #
    def read_transmission_and_rubidium_spectrum(self):
        raise Exception("read_transmission_spectrum not implemented")

    # ------------------ MAIN LOOP ------------------ #
    def main_loop_callback(self):
        pass

    def start(self):
        while not self.stop_condition:
            self.wait()
            transmission_spectrum, rubidium_lines = self.read_transmission_and_rubidium_spectrum()
            if transmission_spectrum is None or rubidium_lines is None:
                time.sleep(self.wait_time)
                continue

            self.update_transmission_spectrum(transmission_spectrum)
            self.update_rubidium_lines(rubidium_lines)

            if not self.calibrate_x_axis():
                continue
            if not self.fit_transmission_spectrum():
                continue

            params = self.cavity.get_fit_parameters() + [self.lock_error]
            self.fit_params_history = np.vstack([self.fit_params_history, params])

            self.main_loop_callback()

            if hasattr(self, "graphics"):
                self.graphics.plot_fit()
                self.graphics.activate_button()
                time.sleep(self.wait_time)


class ScopeResonanceFit(FetchResonanceFit):
    def __init__(self, channels_dict: dict, scope_ip='132.77.54.241', save_data=False):
        save_folder = r'C:\temp\refactor_debug\Experiment_results\QRAM\resonance_params' if save_data else None
        super().__init__(wait_time=0.1, calc_k_ex=False, save_folder=save_folder, save_time=15, show_buttons=True)
        self.save_data = save_data

        if scope_ip is None:
            self.scope = FakeScope(channels_dict)
        else:
            self.scope = Scope(ip=scope_ip)

        self.channels_dict = channels_dict

        rubidium_lines = self.read_scope_data("rubidium")[1]
        self.calibrate_peaks_params_gui(rubidium_lines)

        # Assaf ruined your code
        self.save_path = r'C:\temp\refactor_debug\Experiment_results\QRAM\resonance_params'
        self.last_save_time_k_ex = time.time()

    # ------------------ READ DATA ------------------ #
    def read_scope_data(self, channel):
        channel_number = self.channels_dict[channel]
        time_axis, data = self.scope.get_data(channel_number)
        return time_axis, data

    def read_transmission_and_rubidium_spectrum(self):
        return self.read_transmission_spectrum(), self.read_rubidium_lines()

    def read_transmission_spectrum(self):
        return self.read_scope_data("transmission")[1]

    def read_rubidium_lines(self):
        return self.read_scope_data("rubidium")[1]

    # ------------------ SAVE DATA ------------------ #
    def save_parameter(self):
        if not self.save_data:
            return

        now = round(time.time())
        time_since_last_save = now - self.last_save_time_k_ex
        if time_since_last_save > 3:
            self.last_save_time_k_ex = now
            fwhm_path = os.path.join(self.save_path, "k_ex")
            lock_path = os.path.join(self.save_path, "locking_err")
            print(self.cavity.current_fit_value)
            np.save(fwhm_path, self.cavity.current_fit_value)
            print(self.lock_error)
            np.save(lock_path, self.lock_error)

    def main_loop_callback(self):
        self.save_parameter()


class FolderResonanceFit(FetchResonanceFit):
    cavity_spectrum_regex = re.compile(r"[0-9]+-([0-9]+)_cavity_spectrum.npy")
    rubidium_lines_regex = re.compile(r"[0-9]+-([0-9]+)_rb_lines_spectrum.npy")

    def __init__(self, folder_path, start_time=140000, end_time=180000):
        super().__init__(wait_time=1, calc_k_ex=True, show_buttons=False)
        self.folder_path = folder_path
        self.start_time = start_time
        self.end_time = end_time

        rubidium_lines = next(self.rubidium_lines_generator())
        self.calibrate_peaks_params_gui(rubidium_lines)

        self.transmission_generator = self.transmission_spectrum_generator()
        self.rubidium_lines_generator = self.rubidium_lines_generator()

    def transmission_spectrum_generator(self):
        cavity_spectrum_files = [m for f in os.listdir(self.folder_path)
                                 if (m := self.cavity_spectrum_regex.fullmatch(f))]

        cavity_spectrum_files = filter(lambda m: self.start_time <= int(m[1]) <= self.end_time, cavity_spectrum_files)
        cavity_spectrum_files = sorted(cavity_spectrum_files, key=lambda m: int(m[1]))

        for cavity_spectrum_file in cavity_spectrum_files:
            cavity_spectrum = np.load(os.path.join(self.folder_path, cavity_spectrum_file[0]))
            yield -cavity_spectrum

    def rubidium_lines_generator(self):
        rubidium_lines_files = [m for f in os.listdir(self.folder_path)
                                if (m := self.rubidium_lines_regex.fullmatch(f))]

        rubidium_lines_files = filter(lambda m: self.start_time <= int(m[1]) <= self.end_time, rubidium_lines_files)
        rubidium_lines_files = sorted(rubidium_lines_files, key=lambda m: int(m[1]))

        for rubidium_lines_file in rubidium_lines_files:
            rubidium_lines = np.load(os.path.join(self.folder_path, rubidium_lines_file[0]))
            yield rubidium_lines

    def read_transmission_and_rubidium_spectrum(self):
        return self.read_transmission_spectrum(), self.read_rubidium_lines()

    def read_transmission_spectrum(self):
        transmission_spectrum = next(self.transmission_generator, None)
        self.stop_condition = transmission_spectrum is None
        return transmission_spectrum

    def read_rubidium_lines(self):
        rubidium_spectrum = next(self.rubidium_lines_generator, None)
        self.stop_condition = rubidium_spectrum is None
        return rubidium_spectrum


if __name__ == '__main__':
    # channels = {"transmission": 1, "rubidium": 3}
    # res_fit = ScopeResonanceFit(channels_dict=channels, save_data=False, scope_ip=None)
    # res_fit.start()

    path = r"U:\Lab_2023\Experiment_results\QRAM\Cavity_Spectrum\20240118"
    folder_resonance_fit = FolderResonanceFit(path, start_time=140000, end_time=180000)
    folder_resonance_fit.start()
