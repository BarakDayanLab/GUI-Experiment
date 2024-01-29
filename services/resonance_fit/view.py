import tkinter as tk
import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from .controller import ResonanceFitController
from .model import Model
from queue import Queue
import matplotlib.animation as animation
matplotlib.use('TkAgg')


class App(tk.Tk):
    def __init__(self, cavity, data_loader):
        super().__init__()
        self.queue = Queue(1)

        self.model = Model(cavity)
        self.controller = ResonanceFitController(self, self.model, data_loader)
        self.protocol("WM_DELETE_WINDOW", self.controller.stop)

        self.geometry("1600x800")
        self.wm_title("Resonance Fit")

        self.main_container = tk.Frame(self)
        self.main_container.pack(side="top", fill="both", expand=True)

        self.buttons_container = ButtonsContainer(self.main_container, self)
        self.buttons_container.pack(side="right", fill="both", expand=False)

        self.plot_frame = MatplotlibContainer(self.main_container, self)
        self.plot_frame.pack(side="left", fill="both", expand=False)

        # self.after(1000, self.buttons_container.activate_calibrate_fit_button)

    @staticmethod
    def show_calibration_window(rubidium_spectrum):
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(np.arange(len(rubidium_spectrum)), rubidium_spectrum)
        points = fig.ginput(2, timeout=0, show_clicks=True)
        plt.close(fig)
        return points

    def choose_peak_window(self):
        fig = self.plot_frame.fig

        prev_title = self.plot_frame.title.cget("text")
        self.plot_frame.title.config(text="Choose line")

        point = fig.ginput(1, timeout=0, show_clicks=True)[0]
        self.plot_frame.title.config(text=prev_title)
        self.controller.select_peak(point)


class MatplotlibContainer(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
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
        self.widget.pack(side="top", fill="both", expand=True)

        self.animation = animation.FuncAnimation(self.fig, self.plot_data, interval=40,
                                                 init_func=self.setup_plot, cache_frame_data=False,
                                                 blit=True)

    def plot_data(self, i):
        if self.app.queue.empty():
            return self.get_all_artists()

        data, fit = self.app.queue.get()
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

        self.axes["transmission"].set_ylim(0, 1)

        self.axes["rubidium"].set_ylabel("Rubidium")
        self.axes["rubidium"].set_xlabel("Frequency [MHz]")
        self.axes["rubidium"].grid()

        rubidium_artists = [self.axes["rubidium"].plot([], [])[0],
                            self.axes["rubidium"].scatter([], [], c='r'),
                            self.axes["rubidium"].scatter([], [], c='g')]

        self.axes["rubidium"].set_ylim(0, 1)

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


class ButtonsContainer(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.master = master
        self.app = app

        self.show_error = tk.Button(self, text="Show Error", command=self.activate_show_error_button)
        self.show_error.grid(row=0, column=0, sticky="nsew")

        self.calibrate_fit = tk.Button(self, text="Calibrate Fit", command=self.activate_calibrate_fit_button)
        self.calibrate_fit.grid(row=0, column=1, sticky="nsew")

        self.select_peak = tk.Button(self, text="Select Peak", command=self.activate_select_peak_button)
        self.select_peak.grid(row=1, column=0, sticky="nsew")

    def activate_show_error_button(self):
        self.app.plot_frame.show_error()

    def activate_calibrate_fit_button(self):
        self.app.plot_frame.animation.pause()
        self.app.controller.calibrate_peaks_params()
        self.app.plot_frame.animation.resume()

    def activate_select_peak_button(self):
        self.app.plot_frame.animation.pause()
        self.app.choose_peak_window()
        self.app.plot_frame.animation.resume()
