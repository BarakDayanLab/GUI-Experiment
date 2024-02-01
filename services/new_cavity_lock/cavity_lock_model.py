import os
import time
import numpy as np
from simple_pid import PID
from sched import scheduler
from threading import Lock, Event
from functions.HMP4040Control import HMP4040Visa
from .config import default_parameters, parameter_bounds


class CavityLockModel:
    def __init__(self, data_loader, resonance_fit, save_folder=None):
        self.resonance_fit = resonance_fit
        self.save_folder = save_folder
        self.data_loader = data_loader
        self.data_loader.on_data_callback = self.on_data

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

        self.lock = Lock()
        self.started_event = Event()

        self.scheduler = scheduler(time.time, time.sleep)
        self.save_folder and self.scheduler.enter(5, 1, self.save_spectrum)
        self.scheduler.run(blocking=False)

    def start(self, controller):
        self.controller = controller
        self.data_loader.start()

    def stop(self):
        self.data_loader.stop()

    def on_data(self, data):
        self.lock.acquire()
        if not self.started_event.is_set():
            self.started_event.set()

        self.last_fit_success = self.resonance_fit.fit_data(*data)

        self.lock.release()
        self.last_fit_success and self.update_pid()

    def update_pid(self):
        output = self.pid(self.resonance_fit.lock_error)
        if not self.pid.auto_mode:
            return
        current = self.set_laser_current(output)
        print(output)

    # ------------------ RESONANCE FIT ------------------ #

    def calibrate_peaks_params(self, points):
        self.lock.acquire()
        num_idx_in_peak = np.round(np.abs(points[0][0] - points[1][0]))
        self.resonance_fit.calibrate_peaks_params(num_idx_in_peak)
        self.lock.release()

    def set_selected_peak(self, point):
        self.lock.acquire()
        distances = np.sum((self.resonance_fit.rubidium_peaks - point) ** 2, axis=1)
        self.resonance_fit.lock_idx = np.argmin(distances)
        self.lock.release()

    def get_current_fit(self):
        self.lock.acquire()
        x_axis = self.resonance_fit.x_axis.copy()
        rubidium_lines = self.resonance_fit.rubidium_lines.data.copy()
        transmission_spectrum = self.resonance_fit.cavity.transmission_spectrum.copy()
        data = (x_axis, rubidium_lines, transmission_spectrum)

        if not self.last_fit_success:
            self.lock.release()
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
        self.lock.release()
        return data, fit

    def get_rubidium_lines(self):
        self.lock.acquire()
        rubidium_lines = self.resonance_fit.rubidium_lines.data.copy()
        self.lock.release()
        return rubidium_lines

    # ------------------ DATA LOADER ------------------ #

    def set_data_loader_params(self, params):
        self.data_loader.update(params)

    # ------------------ PID ------------------ #

    def toggle_pid_lock(self, current_value):
        self.lock.acquire()
        self.pid.set_auto_mode(not self.pid.auto_mode, current_value)
        self.lock.release()
        return self.pid.auto_mode

    def set_kp(self, kp):
        self.lock.acquire()
        self.pid.tunings = (kp, self.pid.tunings[1], self.pid.tunings[2])
        self.lock.release()

    def set_ki(self, ki):
        self.lock.acquire()
        self.pid.tunings = (self.pid.tunings[0], ki, self.pid.tunings[2])
        self.lock.release()

    def set_kd(self, kd):
        self.lock.acquire()
        self.pid.tunings = (self.pid.tunings[0], self.pid.tunings[1], kd)
        self.lock.release()

    def set_lock_offset(self, lock_offset):
        self.lock.acquire()
        self.resonance_fit.lock_offset = lock_offset
        self.lock.release()

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

    def get_save_paths(self):
        date = time.strftime("%Y%m%d")
        hours = time.strftime("%H%M%S")

        transmission_filename = f"{date}-{hours}_cavity_spectrum.npy"
        transmission_path = os.path.join(self.save_folder, date, transmission_filename)

        rubidium_filename = f"{date}-{hours}_rubidium_spectrum.npy"
        rubidium_path = os.path.join(self.save_folder, date, rubidium_filename)
        return transmission_path, rubidium_path

    def save_spectrum(self):
        self.lock.acquire()
        transmission_path, rubidium_path = self.get_save_paths()
        np.save(transmission_path, self.resonance_fit.cavity.transmission_spectrum)
        np.save(rubidium_path, self.resonance_fit.rubidium_lines.data)
        self.lock.release()
