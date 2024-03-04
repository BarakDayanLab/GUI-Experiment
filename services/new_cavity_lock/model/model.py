import os
import time
import numpy as np
from services.new_cavity_lock.model.input_output.socket_client import SocketClient
from simple_pid import PID
from threading import Lock
from functions.HMP4040Control import HMP4040Visa
from services.new_cavity_lock.config import default_parameters, parameter_bounds, general as cfg
from services.new_cavity_lock.model.data_processing.fit_handler import FitHandler
from services.new_cavity_lock.model.utilities import use_lock, SetInterval


class CavityLockModel(FitHandler):
    def __init__(self, save=False, use_socket=False, playback_path=None):
        super().__init__(self.update_pid, playback_path)
        self.save = save
        self.use_socket = use_socket

        # The number after the ASRL specifies the COM port where the Hameg is connected, ('ASRL6::INSTR')
        self.hmp4040 = HMP4040Visa(port='ASRL4::INSTR')
        if not hasattr(self.hmp4040, 'inst'):
            self.hmp4040 = None

        self.pid = PID(0, 0, 0, setpoint=0, sample_time=0.1, output_limits=parameter_bounds.HMP_LASER_CURRENT_BOUNDS,
                       auto_mode=False, starting_output=parameter_bounds.HMP_LASER_CURRENT_BOUNDS[0])

        self.controller = None
        self.lock = Lock()

        self.save_interval = SetInterval(cfg.SAVE_INTERVAL, self.save_spectrum)
        self.socket_interval = SetInterval(cfg.SEND_DATA_INTERVAL, self.send_data_socket)
        self.socket = SocketClient(cfg.SOCKET_IP, cfg.SOCKET_PORT, self.socket_connection_status)

    # ------------------ GENERAL ------------------ #

    def start(self, controller):
        self.controller = controller
        self.start_scopes()

        self.save and self.save_interval.start()
        self.use_socket and self.socket_interval.start()
        self.use_socket and self.socket.start()

    def stop(self):
        self.save_interval.cancel()
        self.socket_interval.cancel()
        self.stop_scopes()
        self.use_socket and self.socket.close()

        self.join_scopes()
        self.use_socket and self.socket.join()

    # ------------------ DATA ------------------ #
    @use_lock()
    def calibrate_peaks_params(self, points):
        num_idx_in_peak = np.round(np.abs(points[0][0] - points[1][0]))
        self.calibrate_num_points(num_idx_in_peak)

    # ------------------ RESONANCE FIT ------------------ #

    @use_lock()
    def set_selected_peak(self, point):
        distances = np.sum((self.get_rubidium_peaks() - point) ** 2, axis=1)
        lock_idx = np.argmin(distances)
        self.set_lock_idx(lock_idx)

    # ------------------ PLOT PARAMETERS ------------------ #
    def get_plot_parameters(self):
        data, fit = self.get_current_fit()
        interference_peak = self.get_interference_peak()
        return data, fit, interference_peak

    # ------------------ PID ------------------ #

    def update_pid(self):
        lock_error = self.get_lock_error()
        output = self.pid(lock_error)
        if not self.pid.auto_mode:
            return
        self.set_laser_current(output)
        self.controller.view_get_laser_current()

    @use_lock()
    def toggle_pid_lock(self, current_value):
        self.pid.set_auto_mode(not self.pid.auto_mode, current_value)
        return self.pid.auto_mode

    @use_lock()
    def set_kp(self, kp):
        self.pid.tunings = (kp/cfg.PID_DIVISION, self.pid.tunings[1], self.pid.tunings[2])

    @use_lock()
    def set_ki(self, ki):
        self.pid.tunings = (self.pid.tunings[0], ki/cfg.PID_DIVISION, self.pid.tunings[2])

    @use_lock()
    def set_kd(self, kd):
        self.pid.tunings = (self.pid.tunings[0], self.pid.tunings[1], kd/cfg.PID_DIVISION)

    def set_lock_offset(self, lock_offset):
        super().set_lock_offset(lock_offset)

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

        self.controller.started.wait()
        self.controller.update_socket_status(is_connected)

    @use_lock()
    def send_data_socket(self):
        if not self.last_fit_success:
            return
        k_ex, lock_error, interference_error = self.get_k_ex(), self.get_lock_error(), self.get_interference_error()
        fit_dict = dict(k_ex=k_ex, lock_error=lock_error, interference_error=interference_error)
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

        interference_filename = f"{date}-{hours}_interference_spectrum.npy"
        interference_path = os.path.join(folder_path, interference_filename)
        return transmission_path, rubidium_path, interference_path

    @use_lock()
    def save_spectrum(self):
        if not self.pid.auto_mode:
            return

        transmission_path, rubidium_path, interference_path = self.get_save_paths()
        np.save(transmission_path, self.get_transmission_spectrum())
        np.save(rubidium_path, self.get_rubidium_lines())
        np.save(interference_path, self.get_interference_data())

