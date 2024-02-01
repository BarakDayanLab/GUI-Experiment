from pynput.keyboard import GlobalHotKeys
from .cavity_lock_view import App
from .cavity_lock_model import CavityLockModel
from .config import default_parameters
from services.resonance_fit.data_loader import DataLoaderRedPitaya
import sys


class CavityLockController:
    def __init__(self, model: CavityLockModel):
        self.app = App(self)
        self.model = model

        hotkeys = {"<ctrl>+p": self.app.toggle_pause, }
                   # "<ctrl>+q": self.stop, }
        self.keyboard_listener = GlobalHotKeys(hotkeys)
        self.keyboard_listener.start()

        self.bind_buttons()
        self.bind_pid()
        self.bind_devices()
        # self.model.hmp4040 is not None and self.bind_devices()
        # isinstance(self.model.data_loader, DataLoaderRedPitaya) and self.bind_pid()
        self.update_default_view()

    # ------------------ RUN ------------------ #

    def start(self):
        self.model.start(self)
        self.model.started_event.wait()
        self.update_all_devices()

        self.app.after(500, self.calibrate_peaks_params)
        self.app.mainloop()

    def stop(self, event=None):
        self.stop_model()
        sys.exit(0)

    def stop_model(self):
        self.model.stop()

    def load_fit_data(self):
        self.model.started_event.wait()
        return self.model.get_current_fit()

    def update_all_devices(self):
        if isinstance(self.model.data_loader, DataLoaderRedPitaya):
            self.update_red_pitaya_parameters()
        else:
            self.app.buttons_container.red_pitaya_panel.config(state="disabled")

        if self.model.hmp4040 is not None:
            self.update_kp()
            self.update_ki()
            self.update_kd()
            self.update_lock_offset()

            # self.update_laser_is_checked(self.app.buttons_container.device_control.laser_is_checked.get())
            self.update_laser_current()
            # self.update_halogen_is_checked(self.app.buttons_container.device_control.halogen_is_checked.get())
            self.update_halogen_voltage()
        else:
            self.app.buttons_container.disable_hmp()

    def update_default_view(self):
        self.app.buttons_container.red_pitaya_offset_1.set(default_parameters.CH1_OFFSET)
        self.app.buttons_container.red_pitaya_offset_2.set(default_parameters.CH2_OFFSET)
        self.app.buttons_container.red_pitaya_voltage_1.set(default_parameters.CH1_VOLTAGE)
        self.app.buttons_container.red_pitaya_voltage_2.set(default_parameters.CH2_VOLTAGE)
        self.app.buttons_container.red_pitaya_trigger_level.set(default_parameters.TRIGGER_LEVEL)
        self.app.buttons_container.red_pitaya_trigger_delay.set(default_parameters.TRIGGER_DELAY)

        self.app.buttons_container.pid_control.kp.set(default_parameters.PID_KP)
        self.app.buttons_container.pid_control.ki.set(default_parameters.PID_KI)
        self.app.buttons_container.pid_control.kd.set(default_parameters.PID_KD)
        self.app.buttons_container.pid_control.lock_offset.set(default_parameters.PID_OFFSET)

        self.app.buttons_container.device_control.laser_is_checked.set(default_parameters.HMP_LASER_IS_ON)
        self.app.buttons_container.device_control.laser_current.set(default_parameters.HMP_LASER_CURRENT)
        self.app.buttons_container.device_control.halogen_is_checked.set(default_parameters.HMP_HALOGEN_IS_ON)
        self.app.buttons_container.device_control.halogen_voltage.set(default_parameters.HMP_HALOGEN_VOLTAGE)

    # ------------------ BIND ------------------ #

    def bind_buttons(self):
        self.app.buttons_container.calibrate_fit.bind("<Button-1>", self.calibrate_peaks_params)
        self.app.buttons_container.select_peak.bind("<Button-1>", self.select_peak)
        # self.app.buttons_container.error_signal.bind("<Button-1>", self.show_error_signal)

        self.app.buttons_container.pid_control.lock_offset_control.bind("<Return>", self.update_lock_offset)

    def bind_pid(self):
        self.app.buttons_container.pid_control.kp_control.bind("<<Increment>>", self.update_kp)
        self.app.buttons_container.pid_control.kp_control.bind("<<Decrement>>", self.update_kp)
        self.app.buttons_container.pid_control.ki_control.bind("<<Increment>>", self.update_ki)
        self.app.buttons_container.pid_control.ki_control.bind("<<Decrement>>", self.update_ki)
        self.app.buttons_container.pid_control.kd_control.bind("<<Increment>>", self.update_kd)
        self.app.buttons_container.pid_control.kd_control.bind("<<Decrement>>", self.update_kd)

        self.app.buttons_container.pid_control.start_lock_button.bind("<Button-1>", self.toggle_lock)

    def bind_devices(self):
        self.app.buttons_container.device_control.laser_is_checked.trace_add("write", self.update_laser_is_checked)
        self.app.buttons_container.device_control.laser_current_control.bind("<<Increment>>", self.update_laser_current)
        self.app.buttons_container.device_control.laser_current_control.bind("<<Decrement>>", self.update_laser_current)
        self.app.buttons_container.device_control.halogen_is_checked.trace_add("write", self.update_halogen_is_checked)
        self.app.buttons_container.device_control.halogen_voltage_control.bind("<<Increment>>", self.update_halogen_voltage)
        self.app.buttons_container.device_control.halogen_voltage_control.bind("<<Decrement>>", self.update_halogen_voltage)

    def bind_red_pitaya(self):
        self.app.buttons_container.red_pitaya_panel.update_button.bind("<Button-1>", self.update_red_pitaya_parameters)

    # ------------------ CONTROL FUNCTIONS ------------------ #

    def calibrate_peaks_params(self, event=None):
        rubidium_lines = self.model.get_rubidium_lines()
        points = self.app.show_calibration_window(rubidium_lines)
        self.model.calibrate_peaks_params(points)

    def select_peak(self, event=None):
        point = self.app.choose_peak_window()
        self.model.set_selected_peak(point)

    def show_error_signal(self, event):
        pass

    def update_laser_halogen(self, laser_params, halogen_params):
        voltage, current = laser_params
        self.app.buttons_container.device_control.laser_voltage.set(voltage)
        self.app.buttons_container.device_control.laser_current.set(current)

        voltage, current = halogen_params
        self.app.buttons_container.device_control.halogen_voltage.set(voltage)
        self.app.buttons_container.device_control.halogen_current.set(current)

    # ------------------ LOCK ------------------ #

    def toggle_lock(self, event=None):
        buttons = self.app.buttons_container
        is_active = self.model.toggle_pid_lock(buttons.device_control.laser_current.get())
        buttons.pid_control.active_lock.set(not is_active)
        buttons.pid_control.start_lock_button.config(text="Stop Lock" if is_active else "Start Lock")
        buttons.device_control.laser_is_checked.set(is_active)
        buttons.device_control.laser_current_control.config(state="disabled" if is_active else "normal")
        buttons.device_control.laser_checkbox.config(state="disabled" if is_active else "normal")
        self.app.buttons_container.device_control.laser_is_checked.set(is_active)

    def update_kp(self, event=None):
        self.model.set_kp(-self.app.buttons_container.pid_control.kp.get()/100)

    def update_ki(self, event=None):
        self.model.set_ki(-self.app.buttons_container.pid_control.ki.get()/100)

    def update_kd(self, event=None):
        self.model.set_kd(-self.app.buttons_container.pid_control.kd.get()/100)

    def update_lock_offset(self, event=None):
        self.model.set_lock_offset(self.app.buttons_container.pid_control.lock_offset.get())

    # ------------------ DEVICES ------------------ #

    def update_laser_is_checked(self, *args):
        is_checked = self.app.buttons_container.device_control.laser_is_checked.get()
        self.model.set_laser_on_off(is_checked)

    def update_laser_current(self, event=None):
        self.model.set_laser_current(self.app.buttons_container.device_control.laser_current.get())

    def view_update_laser_current(self):
        current = self.model.get_laser_current()
        self.app.buttons_container.device_control.laser_current.set(current)

    def update_halogen_is_checked(self, *args):
        is_checked = self.app.buttons_container.device_control.halogen_is_checked.get()
        self.model.set_halogen_on_off(is_checked)

    def update_halogen_voltage(self, event=None):
        self.model.set_halogen_voltage(self.app.buttons_container.device_control.halogen_voltage.get())

    def view_update_halogen_voltage(self):
        voltage = self.model.get_halogen_voltage()
        self.app.buttons_container.device_control.halogen_voltage.set(voltage)

    # ------------------ RED PITAYA ------------------ #

    def update_red_pitaya_parameters(self, event=None):
        offset_1 = self.app.buttons_container.red_pitaya_offset_1.get()
        offset_2 = self.app.buttons_container.red_pitaya_offset_2.get()
        voltage_1 = self.app.buttons_container.red_pitaya_voltage_1.get()
        voltage_2 = self.app.buttons_container.red_pitaya_voltage_2.get()
        trigger_level = self.app.buttons_container.red_pitaya_trigger_level.get()
        trigger_delay = self.app.buttons_container.red_pitaya_trigger_delay.get()
        params = {"offset_1": offset_1, "offset_2": offset_2, "voltage_1": voltage_1, "voltage_2": voltage_2,
                  "trigger_level": trigger_level, "trigger_delay": trigger_delay}
        self.model.set_data_loader_params(params)
