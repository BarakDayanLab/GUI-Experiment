import os
import time
import json
import socket
import functools
import numpy as np
from simple_pid import PID
from threading import Lock, Event, Timer, Thread
from functions.HMP4040Control import HMP4040Visa
from .config import default_parameters, parameter_bounds, general as cfg


class SetInterval(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def use_lock(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.lock.acquire()
        result = func(self, *args, **kwargs)
        self.lock.release()
        return result
    return wrapper


class CavityLockModel:
    def __init__(self, data_loader, resonance_fit, save=False, use_socket=False):
        self.resonance_fit = resonance_fit
        self.data_loader = data_loader
        self.data_loader.on_data_callback = self.on_data
        self.save = save
        self.use_socket = use_socket

        try:
            # The number after the ASRL specifies the COM port where the Hameg is connected, ('ASRL6::INSTR')
            self.hmp4040 = HMP4040Visa(port='ASRL4::INSTR')
        except Exception as e:
            print(e)
            self.hmp4040 = None

        self.pid = PID(0, 0, 0, setpoint=0, sample_time=0.1, output_limits=parameter_bounds.HMP_LASER_CURRENT_BOUNDS,
                       auto_mode=False, starting_output=parameter_bounds.HMP_LASER_CURRENT_BOUNDS[0])

        self.controller = None
        self.last_fit_success = False
        self.interval = None

        self.lock = Lock()
        self.started_event = Event()

        self.save_interval = SetInterval(cfg.SAVE_INTERVAL, self.save_spectrum)
        self.socket_interval = SetInterval(cfg.SEND_DATA_INTERVAL, self.send_data_socket)

        if self.use_socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            hostname = socket.gethostname()
            my_ip_address = socket.gethostbyname(hostname)
            print(f'Socket client running on host {hostname}. My IP: {my_ip_address}')
            self.connect_socket()

    # ------------------ GENERAL ------------------ #

    def start(self, controller):
        self.controller = controller
        self.data_loader.start()
        self.started_event.wait()
        self.save and self.save_interval.start()
        self.use_socket and self.socket_interval.start()

    def stop(self):
        self.data_loader.stop()
        self.save_interval.cancel()
        self.socket_interval.cancel()
        self.socket.close()

    def connect_socket(self):
        try:
            self.socket.connect((cfg.SOCKET_IP, cfg.SOCKET_PORT))
        except OSError as e:
            print(e)

    # ------------------ DATA ------------------ #
    @use_lock
    def on_data(self, data):
        self.resonance_fit.set_data(*data)
        if data[1].std() >= 6e-3:
            self.last_fit_success = self.resonance_fit.fit_data()
            self.last_fit_success and self.update_pid()
        else:
            self.last_fit_success = False

        if not self.started_event.is_set():
            self.started_event.set()

    def update_pid(self):
        output = self.pid(self.resonance_fit.lock_error)
        if not self.pid.auto_mode:
            return
        self.set_laser_current(output)
        self.controller.update_laser_view(output)

    # ------------------ RESONANCE FIT ------------------ #
    @use_lock
    def calibrate_peaks_params(self, points):
        num_idx_in_peak = np.round(np.abs(points[0][0] - points[1][0]))
        self.resonance_fit.calibrate_peaks_params(num_idx_in_peak)

    @use_lock
    def set_selected_peak(self, point):
        distances = np.sum((self.resonance_fit.rubidium_peaks - point) ** 2, axis=1)
        self.resonance_fit.lock_idx = np.argmin(distances)

    @use_lock
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

    @use_lock
    def get_rubidium_lines(self):
        rubidium_lines = self.resonance_fit.rubidium_lines.data.copy()
        return rubidium_lines

    # ------------------ DATA LOADER ------------------ #

    def set_data_loader_params(self, params):
        self.data_loader.update(params)

    # ------------------ PID ------------------ #

    @use_lock
    def toggle_pid_lock(self, current_value):
        self.pid.set_auto_mode(not self.pid.auto_mode, current_value)
        return self.pid.auto_mode

    @use_lock
    def set_kp(self, kp):
        self.pid.tunings = (kp, self.pid.tunings[1], self.pid.tunings[2]/cfg.PID_DIVISION)

    @use_lock
    def set_ki(self, ki):
        self.pid.tunings = (self.pid.tunings[0], ki, self.pid.tunings[2]/cfg.PID_DIVISION)

    @use_lock
    def set_kd(self, kd):
        self.pid.tunings = (self.pid.tunings[0], self.pid.tunings[1], kd/cfg.PID_DIVISION)

    @use_lock
    def set_lock_offset(self, lock_offset):
        self.resonance_fit.lock_offset = lock_offset

    # ------------------ HMP ------------------ #

    def set_laser_on_off(self, is_checked):
        self.hmp4040.setOutputChannel(default_parameters.HMP_LASER_CHANNEL)
        self.hmp4040.outputState(int(is_checked))

    def set_laser_current(self, laser_current):
        self.hmp4040.setOutputChannel(default_parameters.HMP_LASER_CHANNEL)
        return self.hmp4040.setCurrent(laser_current)

    def get_laser_current(self):
        self.hmp4040.setOutputChannel(default_parameters.HMP_LASER_CHANNEL)
        return self.hmp4040.getCurrent()

    def get_laser_voltage(self):
        self.hmp4040.setOutputChannel(default_parameters.HMP_LASER_CHANNEL)
        return self.hmp4040.getVoltage()

    def set_halogen_on_off(self, is_checked):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        self.hmp4040.outputState(int(is_checked))

    def set_halogen_voltage(self, halogen_voltage):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        return self.hmp4040.setVoltage(halogen_voltage)

    def get_halogen_voltage(self):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        return self.hmp4040.getVoltage()

    # ------------------ SAVE DATA ------------------ #
    @staticmethod
    def get_save_paths():
        date = time.strftime("%Y%m%d")
        hours = time.strftime("%H%M%S")

        folder_path = os.path.join(cfg.FOLDER_PATH, date)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        transmission_filename = f"{date}-{hours}_cavity_spectrum.npy"
        transmission_path = os.path.join(folder_path, transmission_filename)

        rubidium_filename = f"{date}-{hours}_rubidium_spectrum.npy"
        rubidium_path = os.path.join(folder_path, rubidium_filename)
        return transmission_path, rubidium_path

    @use_lock
    def save_spectrum(self):
        transmission_path, rubidium_path = self.get_save_paths()
        np.save(transmission_path, self.resonance_fit.cavity.transmission_spectrum)
        np.save(rubidium_path, self.resonance_fit.rubidium_lines.data)

    @use_lock
    def send_data_socket(self):
        # if not self.last_fit_success:
        #     return
        # fit_dict = dict(k_ex=self.resonance_fit.cavity.current_fit_value, lock_error=self.resonance_fit.lock_error)
        fit_dict = dict(k_ex=0, lock_error=0)
        message = json.dumps(fit_dict)
        try:
            self.socket.send(message.encode())
        except OSError as e:
            self.socket.close()
            Thread(target=self.connect_socket).start()
