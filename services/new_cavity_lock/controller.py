import time

from .model import CavityLockModel
from services.resonance_fit.data_loader import DataLoaderRedPitaya
import sys
from .view import App


class CavityLockController:
    def __init__(self, save, use_socket):
        self.app = App(self)
        self.model = CavityLockModel(save=save, use_socket=use_socket)

        self.bind_general_controls()
        self.bind_pid_controls()
        self.bind_hmp_controls()

    # ------------------ RUN ------------------ #

    def start(self):
        self.model.start(self)
        self.update_all_devices()
        self.calibrate_peaks_params()

        self.app.main_window.showMaximized()
        sys.exit(self.app.exec())

    def stop(self, event=None):
        self.stop_model()
        sys.exit(0)

    def stop_model(self):
        self.model.stop()

    def load_fit_data(self):
        self.model.started_event.wait()
        return self.model.get_plot_parameters()

    def update_all_devices(self):
        if isinstance(self.model.resonance_fit_data_loader, DataLoaderRedPitaya):
            self.update_red_pitaya_parameters()
        else:
            self.app.general_controls.red_pitaya_panel.setEnabled(False)

        self.update_lock_offset()

        if self.model.hmp4040 is None:
            self.app.disable_hmp()
        else:
            self.update_kp()
            self.update_ki()
            self.update_kd()

            self.view_get_laser_is_checked()
            self.view_get_laser_current()
            self.view_get_halogen_is_checked()
            self.view_get_halogen_voltage()

    # ------------------ BIND ------------------ #
    # noinspection PyUnresolvedReferences
    def bind_general_controls(self):
        self.app.general_controls.lock_error_button.clicked.connect(self.show_error_signal)
        self.app.general_controls.calibrate_fit.clicked.connect(self.calibrate_peaks_params)
        self.app.general_controls.select_peak.clicked.connect(self.select_peak)

    # noinspection PyUnresolvedReferences
    def bind_pid_controls(self):
        self.app.pid_control.start_lock_button.clicked.connect(self.toggle_lock)
        self.app.pid_control.kp_control.valueChanged.connect(self.update_kp)
        self.app.pid_control.ki_control.valueChanged.connect(self.update_ki)
        self.app.pid_control.kd_control.valueChanged.connect(self.update_kd)
        self.app.pid_control.lock_offset_control.valueChanged.connect(self.update_lock_offset)

    # noinspection PyUnresolvedReferences
    def bind_hmp_controls(self):
        self.app.hmp_control.laser_checkbox.stateChanged.connect(self.update_laser_is_checked)
        self.app.hmp_control.laser_current_control.valueChanged.connect(self.update_laser_current)
        self.app.hmp_control.halogen_checkbox.stateChanged.connect(self.update_halogen_is_checked)
        self.app.hmp_control.halogen_voltage_control.valueChanged.connect(self.update_halogen_voltage)

    # ------------------ CONTROL FUNCTIONS ------------------ #

    def show_error_signal(self, event):
        pass

    def calibrate_peaks_params(self, event=None):
        rubidium_lines = self.model.get_rubidium_lines()
        points = self.app.show_calibration_window(rubidium_lines)
        self.model.calibrate_peaks_params(points)

    def select_peak(self, event=None):
        point = self.app.choose_peak_window()
        self.model.set_selected_peak(point)

    # ------------------ LOCK ------------------ #

    def toggle_lock(self, event=None):
        is_active = self.model.toggle_pid_lock(self.app.hmp_control.laser_checkbox.isChecked())
        self.app.pid_control.start_lock_button.setText("Stop Lock" if is_active else "Start Lock")
        self.app.hmp_control.laser_checkbox.setChecked(is_active)
        self.app.hmp_control.laser_current_control.setDisabled(is_active)
        self.app.hmp_control.laser_checkbox.setDisabled(is_active)

    def update_kp(self, event=None):
        self.model.set_kp(-self.app.pid_control.kp_control.value())

    def update_ki(self, event=None):
        self.model.set_ki(-self.app.pid_control.ki_control.value())

    def update_kd(self, event=None):
        self.model.set_kd(-self.app.pid_control.kd_control.value())

    def update_lock_offset(self, event=None):
        self.model.set_lock_offset(self.app.pid_control.lock_offset_control.value())

    # ------------------ DEVICES ------------------ #

    def update_laser_is_checked(self, *args):
        is_checked = self.app.hmp_control.laser_checkbox.isChecked()
        self.model.set_laser_on_off(is_checked)

    def view_get_laser_is_checked(self):
        is_checked = self.model.get_laser_on_off()
        self.app.hmp_control.laser_checkbox.setChecked(is_checked)

    def update_laser_current(self, event=None):
        self.model.set_laser_current(self.app.hmp_control.laser_current_control.value())

    def view_get_laser_current(self):
        current = self.model.get_laser_current()
        self.app.hmp_control.laser_current_control.setValue(current)

    def update_halogen_is_checked(self, *args):
        is_checked = self.app.hmp_control.halogen_checkbox.isChecked()
        self.model.set_halogen_on_off(is_checked)

    def view_get_halogen_is_checked(self):
        is_checked = self.model.get_halogen_on_off()
        self.app.hmp_control.halogen_checkbox.setChecked(is_checked)

    def update_halogen_voltage(self, event=None):
        self.model.set_halogen_voltage(self.app.hmp_control.halogen_voltage_control.value())

    def view_get_halogen_voltage(self):
        voltage = self.model.get_halogen_voltage()
        self.app.hmp_control.halogen_voltage_control.setValue(voltage)

    # ------------------ RED PITAYA ------------------ #

    def update_red_pitaya_parameters(self, event=None):
        self.model.set_data_loader_params(self.app.red_pitaya_params)

    # ------------------ CONNECTION PANEL ------------------ #
    def update_socket_status(self, status):
        self.app.connection_panel.set_connection_led_status(status)
