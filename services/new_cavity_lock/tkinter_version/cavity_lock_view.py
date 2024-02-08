import tkinter as tk
from tkinter import ttk
import sys
import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.animation as animation
from services.new_cavity_lock.config import parameter_bounds
matplotlib.use('TkAgg')


class App(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.pause = False

        style = ttk.Style(self)
        self.tk.call("source", "forest-dark.tcl")
        style.theme_use("forest-dark")

        self.protocol("WM_DELETE_WINDOW", self.stop)
        self.geometry("1600x800")
        self.wm_title("Cavity Lock")

        self.main_container = tk.Frame(self)
        self.main_container.pack(side="top", fill="both", expand=True, padx=20, pady=20)

        self.buttons_container = ButtonsContainer(self.main_container, self)
        self.buttons_container.pack(side="right", fill="y", padx=20)

        self.plot_frame = MatplotlibContainer(self.main_container, self)
        self.plot_frame.pack(side="left", fill="both", expand=True)

    def stop(self):
        self.controller.stop()

    def toggle_pause(self):
        self.pause = not self.pause
        if self.pause:
            self.plot_frame.animation.pause()
        else:
            self.plot_frame.animation.resume()

    def show_calibration_window(self, rubidium_spectrum):
        self.toggle_pause()
        fig, ax = plt.subplots(figsize=(16, 5))
        ax.plot(np.arange(len(rubidium_spectrum)), rubidium_spectrum)
        points = fig.ginput(2, timeout=0, show_clicks=True)
        plt.close(fig)
        self.toggle_pause()
        return points

    def choose_peak_window(self):
        self.toggle_pause()
        fig = self.plot_frame.fig
        prev_title = self.plot_frame.title.cget("text")
        self.plot_frame.title.config(text="Choose line")

        point = fig.ginput(1, timeout=0, show_clicks=True)[0]
        self.plot_frame.title.config(text=prev_title)
        self.toggle_pause()
        return point


class MatplotlibContainer(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, style='Card', padding=(5, 5, 5, 5))
        self.master = master
        self.app = app
        self.title = tk.Label(self, text="", justify="center", font=("Helvetica", 28))
        self.title.pack(side="top", fill="both", expand=True)

        self.fig = plt.figure(dpi=100)
        axes = self.fig.subplots(2, 1, sharex="all")
        self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        self.axes = {"transmission": axes[0], "rubidium": axes[1]}

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.widget = self.canvas.get_tk_widget()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.widget.pack(side="bottom", fill="both", expand=True)

        self.animation = animation.FuncAnimation(self.fig, self.plot_data, interval=50,
                                                 init_func=self.setup_plot, cache_frame_data=False,
                                                 blit=True)

    def plot_data(self, i):
        data, fit = self.app.controller.load_fit_data()
        self.plot_spectrum(*data)

        if fit is not None:
            self.plot_fit(*fit)
            return self.get_all_artists()
        self.remove_fit()
        return self.get_data_artists()

    def setup_plot(self):
        self.axes["transmission"].set_ylabel("Transmission")
        self.axes["transmission"].grid()

        transmission_artists = [self.axes["transmission"].plot([], [])[0],
                                self.axes["transmission"].plot([], [])[0],
                                self.axes["transmission"].scatter([], [], c='g')]

        self.axes["transmission"].set_ylim(-0.1, 1)

        self.axes["rubidium"].set_ylabel("Rubidium")
        self.axes["rubidium"].set_xlabel("Frequency [MHz]")
        self.axes["rubidium"].grid()

        rubidium_artists = [self.axes["rubidium"].plot([], [])[0],
                            self.axes["rubidium"].plot([], [])[0],
                            self.axes["rubidium"].scatter([], [], c='r'),
                            self.axes["rubidium"].scatter([], [], c='g')]

        self.axes["rubidium"].set_ylim(-0.1, 1.1)

        return *transmission_artists, *rubidium_artists

    def get_data_artists(self):
        transmission_artist = self.axes["transmission"].get_lines()[0]
        rubidium_artist = self.axes["rubidium"].get_lines()[0]
        return transmission_artist, rubidium_artist

    def get_all_artists(self):
        transmission_artists = [*self.axes["transmission"].get_lines(),
                                *self.axes["transmission"].collections]

        rubidium_artists = [*self.axes["rubidium"].get_lines(),
                            *self.axes["rubidium"].collections]

        return *transmission_artists, *rubidium_artists

    def plot_rubidium(self, x_axis, rubidium_spectrum):
        lines = self.axes["rubidium"].get_lines()
        lines[0].set_data(x_axis, rubidium_spectrum)
        # lines[1].set_data(x_axis, self.app.model.enhance_peaks(rubidium_spectrum))
        self.axes["rubidium"].set_xlim(x_axis[0], x_axis[-1])

    def plot_rubidium_peaks(self, rubidium_peaks, selected_peak):
        collections = self.axes["rubidium"].collections
        collections[0].set_offsets(rubidium_peaks)
        collections[1].set_offsets(selected_peak)

    def plot_transmission(self, x_axis, transmission_spectrum):
        lines = self.axes["transmission"].get_lines()
        lines[0].set_data(x_axis, transmission_spectrum)
        self.axes["transmission"].set_xlim(x_axis[0], x_axis[-1])

    def plot_transmission_fit(self, x_axis, fit, x_0):
        lines = self.axes["transmission"].get_lines()
        lines[1].set_data(x_axis, fit)
        collections = self.axes["transmission"].collections
        collections[0].set_offsets(x_0)

    def plot_spectrum(self, x_axis, rubidium_spectrum, transmission_spectrum):
        self.plot_rubidium(x_axis, rubidium_spectrum)
        self.plot_transmission(x_axis, transmission_spectrum)

    def plot_fit(self, x_axis, rubidium_peaks, selected_peak, x_0, transmission_fit, title=None):
        self.title.config(text=title or "")
        self.plot_transmission_fit(x_axis, transmission_fit, x_0)
        self.plot_rubidium_peaks(rubidium_peaks, selected_peak)

    def remove_fit(self):
        self.title.config(text="Error")


class ButtonsContainer(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, style='Card', padding=(5, 5, 5, 5))
        self.master = master
        self.app = app
        self.popup = None

        self.red_pitaya_offset_1 = tk.DoubleVar()
        self.red_pitaya_offset_2 = tk.DoubleVar()
        self.red_pitaya_voltage_1 = tk.DoubleVar()
        self.red_pitaya_voltage_2 = tk.DoubleVar()
        self.red_pitaya_trigger_level = tk.DoubleVar()
        self.red_pitaya_trigger_delay = tk.DoubleVar()

        # self.show_error = ttk.Button(self, text="Show Error", command=self.activate_show_error_button, width=15)
        # self.show_error.grid(row=0, column=0, sticky="nsew")
        self.calibrate_fit = ttk.Button(self, text="Calibrate Fit")
        self.calibrate_fit.grid(row=0, column=1, padx=10, pady=10, sticky="we")
        self.select_peak = ttk.Button(self, text="Select Peak")
        self.select_peak.grid(row=1, column=0, padx=10, pady=10, sticky="we")
        self.red_pitaya_panel = ttk.Button(self, text="RedPitaya", command=self.activate_pid_panel_button)
        self.red_pitaya_panel.grid(row=1, column=1, padx=10, pady=10, sticky="we")

        ttk.Separator(self, orient='horizontal').grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="we")

        self.pid_control = PidControl(self, self.app)
        self.pid_control.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="we")

        ttk.Separator(self, orient='horizontal').grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="we")

        self.device_control = DeviceControl(self, self.app)
        self.device_control.grid(row=5, column=0, columnspan=2)

    def activate_pid_panel_button(self):
        parameters = (self.red_pitaya_offset_1, self.red_pitaya_offset_2, self.red_pitaya_voltage_1,
                      self.red_pitaya_voltage_2, self.red_pitaya_trigger_level, self.red_pitaya_trigger_delay)
        self.popup = RedPitayaControlPanel(self, self.app, self.update_red_pitaya, self.close_popup, parameters)
        self.popup.grab_set()

    def update_red_pitaya(self):
        self.close_popup()

    def close_popup(self):
        self.popup.grab_release()
        self.popup.destroy()
        self.popup = None

    def disable_hmp(self):
        self.device_control.laser_checkbox.config(state="disabled")
        self.device_control.laser_current_control.config(state="disabled")
        self.device_control.halogen_checkbox.config(state="disabled")
        self.device_control.halogen_voltage_control.config(state="disabled")

        self.pid_control.start_lock_button.config(state="disabled")
        self.pid_control.kp_control.config(state="disabled")
        self.pid_control.ki_control.config(state="disabled")
        self.pid_control.kd_control.config(state="disabled")


class DeviceControl(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.master = master
        self.app = app

        self.laser_is_checked = tk.BooleanVar()
        self.laser_current = tk.DoubleVar()
        self.halogen_is_checked = tk.BooleanVar()
        self.halogen_voltage = tk.DoubleVar()

        self.device_control_title = ttk.Label(self, text="Device Control", font=('Helvetica', 16, "bold"))
        self.device_control_title.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        start, end = parameter_bounds.HMP_LASER_CURRENT_BOUNDS
        self.laser_checkbox = ttk.Checkbutton(self, text="Laser[current]:", variable=self.laser_is_checked)
        self.laser_checkbox.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.laser_current_control = ttk.Spinbox(self, from_=start, to=end, increment=0.01, format="%.2f", textvariable=self.laser_current, width=10, state="readonly")
        self.laser_current_control.grid(row=2, column=1, padx=10, pady=10)

        start, end = parameter_bounds.HMP_HALOGEN_VOLTAGE_BOUNDS
        self.halogen_checkbox = ttk.Checkbutton(self, text="Halogen[voltage]:", variable=self.halogen_is_checked)
        self.halogen_checkbox.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.halogen_voltage_control = ttk.Spinbox(self, from_=start, to=end, increment=0.1, format="%.1f", textvariable=self.halogen_voltage, width=10, state="readonly")
        self.halogen_voltage_control.grid(row=3, column=1, padx=10, pady=10)


class PidControl(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.active_lock = tk.BooleanVar(value=False)
        self.kp = tk.DoubleVar()
        self.ki = tk.DoubleVar()
        self.kd = tk.DoubleVar()
        self.lock_offset = tk.DoubleVar()

        self.pid_controls_title = ttk.Label(self, text="PID Controls", font=('Helvetica', 16, "bold"))
        self.pid_controls_title.grid(row=0, column=0, columnspan=6, padx=10, pady=10)

        self.kp_label = ttk.Label(self, text="P:", font=('Helvetica', 12, "bold"))
        self.kp_label.grid(row=1, column=0)
        self.kp_control = ttk.Spinbox(self, from_=0, to=10, increment=0.1, format="%.1f", textvariable=self.kp, width=6)
        self.kp_control.grid(row=1, column=1, padx=10, pady=10)

        self.ki_label = ttk.Label(self, text="I:", font=('Helvetica', 12, "bold"))
        self.ki_label.grid(row=1, column=2)
        self.ki_control = ttk.Spinbox(self, from_=0, to=10, increment=0.1, format="%.1f", textvariable=self.ki, width=6)
        self.ki_control.grid(row=1, column=3, padx=10, pady=10)

        self.kd_label = ttk.Label(self, text="D:", font=('Helvetica', 12, "bold"))
        self.kd_label.grid(row=1, column=4)
        self.kd_control = ttk.Spinbox(self, from_=0, to=10, increment=0.1, format="%.1f", textvariable=self.kd, width=6)
        self.kd_control.grid(row=1, column=5, padx=10, pady=10)

        start, end = parameter_bounds.PID_OFFSET_BOUNDS
        self.lock_offset_label = ttk.Label(self, text="Lock Offset:", font=('Helvetica', 12, "bold"))
        self.lock_offset_label.grid(row=2, column=0, columnspan=3)
        self.lock_offset_control = ttk.Spinbox(self, from_=start, to=end, increment=0.5, format="%.1f", textvariable=self.lock_offset)
        self.lock_offset_control.grid(row=2, column=3, columnspan=3, padx=10, pady=10)

        self.start_lock_button = ttk.Checkbutton(self, text="Start Lock", style='ToggleButton', variable=self.active_lock, width=20)
        self.start_lock_button.grid(row=3, column=0, columnspan=6, padx=10, pady=10)


class RedPitayaControlPanel(tk.Toplevel):
    def __init__(self, master, app, update_callback, cancel_callback, params):
        super().__init__(master)
        self.master = master
        self.app = app
        self.update_callback = update_callback
        self.cancel_callback = cancel_callback

        self.offset_1 = params[0]
        self.offset_2 = params[1]
        self.voltage_1 = params[2]
        self.voltage_2 = params[3]
        self.trigger_level = params[4]
        self.trigger_delay = params[5]

        x = app.winfo_x() + app.winfo_width() // 2 - self.winfo_width() // 2
        y = app.winfo_y() + app.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")

        self.frame = ttk.Frame(self)
        self.frame.pack(fill="both", expand=True)

        self.title("Red Pitaya Control Panel")

        self.channel_1_label = ttk.Label(self.frame, text="Channel 1", font=('Helvetica', 12, "bold"))
        self.channel_1_label.grid(row=0, column=1, padx=10, sticky="nw")
        self.channel_2_label = ttk.Label(self.frame, text="Channel 2", font=('Helvetica', 12, "bold"))
        self.channel_2_label.grid(row=0, column=2, padx=10, sticky="nw")

        start, end = parameter_bounds.RED_PITAYA_OFFSET_BOUNDS
        self.offset_label = ttk.Label(self.frame, text="Offset:", font=('Helvetica', 12, "bold"))
        self.offset_label.grid(row=1, column=0, sticky="nw")
        self.offset_control_1 = ttk.Spinbox(self.frame, from_=start, to=end, increment=0.1, format="%.1f", textvariable=self.offset_1)
        self.offset_control_1.grid(row=1, column=1, padx=10)
        self.offset_control_2 = ttk.Spinbox(self.frame, from_=start, to=end, increment=0.1, format="%.1f", textvariable=self.offset_2)
        self.offset_control_2.grid(row=1, column=2, padx=10)

        start, end = parameter_bounds.RED_PITAYA_VOLTAGE_BOUNDS
        self.voltage_label = ttk.Label(self.frame, text="Voltage:", font=('Helvetica', 12, "bold"))
        self.voltage_label.grid(row=2, column=0, sticky="nw")
        self.voltage_control_1 = ttk.Spinbox(self.frame, from_=start, to=end, increment=0.1, format="%.1f", textvariable=self.voltage_1)
        self.voltage_control_1.grid(row=2, column=1, padx=10)
        self.voltage_control_2 = ttk.Spinbox(self.frame, from_=start, to=end, increment=0.1, format="%.1f", textvariable=self.voltage_2)
        self.voltage_control_2.grid(row=2, column=2, padx=10)

        ttk.Separator(self.frame, orient='horizontal').grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="we")

        self.trigger_level_label = ttk.Label(self.frame, text="Level", font=('Helvetica', 12, "bold"))
        self.trigger_level_label.grid(row=4, column=1, padx=10, sticky="nw")
        self.trigger_delay_label = ttk.Label(self.frame, text="Delay", font=('Helvetica', 12, "bold"))
        self.trigger_delay_label.grid(row=4, column=2, padx=10, sticky="nw")

        start, end = parameter_bounds.RED_PITAYA_TRIGGER_LEVEL_BOUNDS
        self.trigger_label = ttk.Label(self.frame, text="Trigger:", font=('Helvetica', 12, "bold"))
        self.trigger_label.grid(row=5, column=0, sticky="nw")
        self.trigger_control_1 = ttk.Spinbox(self.frame, from_=start, to=end, increment=0.1, format="%.1f", textvariable=self.trigger_level)
        self.trigger_control_1.grid(row=5, column=1, padx=10)
        self.trigger_control_2 = ttk.Spinbox(self.frame, from_=start, to=end, increment=0.1, format="%.1f", textvariable=self.trigger_delay)
        self.trigger_control_2.grid(row=5, column=2, padx=10)

        self.cancel_button = ttk.Button(self.frame, text="Cancel", command=self.close)
        self.cancel_button.grid(row=6, column=1, padx=10, pady=10, sticky="we")
        self.update_button = ttk.Button(self.frame, text="Update", style='Accent.TButton', command=self.update)
        self.update_button.grid(row=6, column=2, padx=10, pady=10, sticky="we")

    def update(self):
        self.update_callback()

    def close(self):
        self.cancel_callback()
