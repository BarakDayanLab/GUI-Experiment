import os
import time
import functools
import numpy as np
from .socket_client import SocketClient
from simple_pid import PID
from threading import Lock, Event, Timer
from functions.HMP4040Control import HMP4040Visa
from .config import default_parameters, parameter_bounds, general as cfg
from services.resonance_fit import ResonanceFit, CavityKex, DataLoaderRedPitaya, ScopeDataLoader
from .interference import InterferenceFit


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
    def __init__(self, save=False, use_socket=False):
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

        # self.resonance_fit_data_loader = ScopeDataLoader(channels_dict={"transmission": 1, "rubidium": 2}, scope_ip=None)
        self.resonance_fit_data_loader = DataLoaderRedPitaya(host="rp-ffffb4.local")
        self.resonance_fit_data_loader.on_data_callback = self.on_data

        cavity = CavityKex(k_i=0, h=0)
        self.resonance_fit = ResonanceFit(cavity)

        self.interference_data_loader = DataLoaderRedPitaya(host="rp-ffff3e.local")
        self.interference_data_loader.on_data_callback = self.on_interference_data
        self.interference_fit = InterferenceFit(avg_num=2)

        self.controller = None
        self.last_fit_success = False
        self.lock = Lock()
        self.started_resonance_fit_event = Event()
        self.started_interference_event = Event()

        self.save_interval = SetInterval(cfg.SAVE_INTERVAL, self.save_spectrum)
        self.socket_interval = SetInterval(cfg.SEND_DATA_INTERVAL, self.send_data_socket)
        self.socket = SocketClient(cfg.SOCKET_IP, cfg.SOCKET_PORT, self.socket_connection_status)

    # ------------------ GENERAL ------------------ #

    def start(self, controller):
        self.controller = controller
        self.resonance_fit_data_loader.start()
        self.interference_data_loader.start()
        self.started_resonance_fit_event.wait()
        self.started_interference_event.wait()

        self.save and self.save_interval.start()
        self.use_socket and self.socket_interval.start()
        self.use_socket and self.socket.start()

    def stop(self):
        self.save_interval.cancel()
        self.socket_interval.cancel()
        self.resonance_fit_data_loader.stop()
        self.interference_data_loader.stop()
        self.use_socket and self.socket.close()

        self.resonance_fit_data_loader.join()
        self.interference_data_loader.join()
        self.use_socket and self.socket.join()

    # ------------------ DATA ------------------ #\
    @use_lock
    def on_interference_data(self, data):
        self.interference_fit.calculate_peak_idx(data[1])

        if not self.started_interference_event.is_set():
            self.started_interference_event.set()

    @use_lock
    def on_data(self, data):
        self.resonance_fit.set_data(*data.copy())
        if data[1].std() >= 6e-3:
            self.last_fit_success = self.resonance_fit.fit_data()
            if self.last_fit_success:
                if len(self.resonance_fit.fit_params_history) < 2 or \
                        np.abs(self.resonance_fit.fit_params_history[-1, -1] - self.resonance_fit.fit_params_history[-2, -1]) < 10:
                    self.update_pid()
        else:
            self.last_fit_success = False

        if not self.started_resonance_fit_event.is_set():
            self.started_resonance_fit_event.set()

    @use_lock
    def calibrate_peaks_params(self, points):
        num_idx_in_peak = np.round(np.abs(points[0][0] - points[1][0]))
        self.resonance_fit.calibrate_peaks_params(num_idx_in_peak)

    # ------------------ RESONANCE FIT ------------------ #

    @use_lock
    def set_selected_peak(self, point):
        distances = np.sum((self.resonance_fit.rubidium_peaks - point) ** 2, axis=1)
        self.resonance_fit.lock_idx = np.argmin(distances)

    @use_lock
    def set_kappa_i(self, kappa_i):
        self.resonance_fit.cavity.k_i = kappa_i

    @use_lock
    def set_h(self, h):
        self.resonance_fit.cavity.h = h

    @use_lock
    def get_current_fit(self):
        x_axis = self.resonance_fit.x_axis.copy()
        rubidium_lines = self.resonance_fit.rubidium_lines.data.copy()
        transmission_spectrum = self.resonance_fit.cavity.transmission_spectrum.copy()
        data = (x_axis, rubidium_lines, transmission_spectrum)

        if not self.last_fit_success:
            return data, None

        lock_error = self.resonance_fit.lock_error
        # print(self.resonance_fit.fit_params_history[-20:, -1].std())
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

    # ------------------ INTERFERENCE FIT ------------------ #

    @use_lock
    def get_interference_peak(self):
        peak_idx = self.interference_fit.peak_idx
        # return self.resonance_fit.x_axis[peak_idx]
        return self.interference_fit.prev_data.mean(axis=0)

    # ------------------ PLOT PARAMETERS ------------------ #
    def get_plot_parameters(self):
        data, fit = self.get_current_fit()
        interference_peak = self.get_interference_peak()
        return data, fit, interference_peak

    # ------------------ DATA LOADER ------------------ #

    def set_data_loader_params(self, params):
        self.resonance_fit_data_loader.update(params)
        self.interference_data_loader.update(params)

    # ------------------ PID ------------------ #

    def update_pid(self):
        output = self.pid(self.resonance_fit.lock_error)
        if not self.pid.auto_mode:
            return
        self.set_laser_current(output)
        self.controller.view_get_laser_current()

    @use_lock
    def toggle_pid_lock(self, current_value):
        self.pid.set_auto_mode(not self.pid.auto_mode, current_value)
        return self.pid.auto_mode

    @use_lock
    def set_kp(self, kp):
        self.pid.tunings = (kp/cfg.PID_DIVISION, self.pid.tunings[1], self.pid.tunings[2])

    @use_lock
    def set_ki(self, ki):
        self.pid.tunings = (self.pid.tunings[0], ki/cfg.PID_DIVISION, self.pid.tunings[2])

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

    def get_laser_on_off(self):
        self.hmp4040.setOutputChannel(default_parameters.HMP_LASER_CHANNEL)
        return bool(self.hmp4040.getOutputState())

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

    def get_halogen_on_off(self):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        return bool(self.hmp4040.getOutputState())

    def set_halogen_voltage(self, halogen_voltage):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        return self.hmp4040.setVoltage(halogen_voltage)

    def get_halogen_voltage(self):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        return self.hmp4040.getVoltage()

    def set_halogen_current(self, halogen_current):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        return self.hmp4040.setCurrent(halogen_current)

    def get_halogen_current(self):
        self.hmp4040.setOutputChannel(default_parameters.HMP_HALOGEN_CHANNEL)
        return self.hmp4040.getCurrent()

    # ------------------ SOCKET ------------------ #
    def socket_connection_status(self, is_connected):
        if is_connected:
            hostname, my_ip_address = self.socket.get_host_ip()
            print(f'Socket client running on host {hostname}. IP: {my_ip_address}')
        else:
            print("connection to socket server lost. Trying to reconnect...")

        self.controller.update_socket_status(is_connected)

    @use_lock
    def send_data_socket(self):
        if not self.last_fit_success:
            return
        fit_dict = dict(k_ex=self.resonance_fit.cavity.current_fit_value, lock_error=self.resonance_fit.lock_error)
        self.socket.send_data(fit_dict)

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
