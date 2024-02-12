import sys
import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
import matplotlib.animation as animation
from .config import parameter_bounds, default_parameters
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import Qt
import qdarktheme
# from qt_material import apply_stylesheet
matplotlib.use('QtAgg')


class App(QtWidgets.QApplication):
    def __init__(self, controller):
        qdarktheme.enable_hi_dpi()
        super().__init__(sys.argv)
        qdarktheme.setup_theme()
        # apply_stylesheet(self, theme='dark_cyan.xml')

        self.controller = controller
        self.main_window = MainWindow(self)
        self.pause = False
        self.red_pitaya_popup = None

        self.plot_frame = self.main_window.plot_frame
        self.general_controls = self.main_window.buttons_container.general_controls
        self.pid_control = self.main_window.buttons_container.pid_control
        self.hmp_control = self.main_window.buttons_container.hmp_control
        self.connection_panel = self.main_window.buttons_container.connection_panel

        # noinspection PyUnresolvedReferences
        self.general_controls.red_pitaya_panel.clicked.connect(self.activate_red_pitaya_panel_button)
        self.red_pitaya_params = self.get_default_red_pitaya_parameters()

        self.set_default_pid_parameters()
        self.set_default_hmp_parameters()

    def start(self):
        self.main_window.show()

    # ------------------ PLOTS ------------------ #

    def toggle_pause(self):
        self.pause = not self.pause
        if self.pause:
            self.plot_frame.animation.event_source.stop()
        else:
            self.plot_frame.animation.event_source.start()

    def show_error_signal(self):
        pass

    def show_calibration_window(self, rubidium_spectrum):
        self.toggle_pause()
        fig, ax = plt.subplots(figsize=(16, 5))
        ax.set_title("Choose 2 points around the highest peak")
        ax.plot(np.arange(len(rubidium_spectrum)), rubidium_spectrum)
        points = plt.ginput(2, timeout=0, show_clicks=True)
        plt.close(fig)
        self.toggle_pause()
        return points

    def choose_peak_window(self):
        self.toggle_pause()
        prev_title = self.plot_frame.title.text()
        self.plot_frame.title.setText("Choose line")

        point = self.plot_frame.fig.ginput(1, timeout=0, show_clicks=True)[0]
        self.plot_frame.title.setText(prev_title)
        self.toggle_pause()
        return point

    # ------------------ RED PITAYA ------------------ #

    def activate_red_pitaya_panel_button(self):
        self.red_pitaya_popup = RedPitayaControlPanel(self.main_window, self.red_pitaya_params, self.update_red_pitaya_parameters)
        self.red_pitaya_popup.setModal(True)
        self.red_pitaya_popup.show()

    def update_red_pitaya_parameters(self):
        self.red_pitaya_params["offset_1"] = self.red_pitaya_popup.offset_control_1.value()
        self.red_pitaya_params["offset_2"] = self.red_pitaya_popup.offset_control_2.value()
        self.red_pitaya_params["voltage_1"] = self.red_pitaya_popup.voltage_control_1.value()
        self.red_pitaya_params["voltage_2"] = self.red_pitaya_popup.voltage_control_2.value()
        self.red_pitaya_params["trigger_level"] = self.red_pitaya_popup.trigger_control_1.value()
        self.red_pitaya_params["trigger_delay"] = self.red_pitaya_popup.trigger_control_2.value()
        self.red_pitaya_params["time_scale"] = self.red_pitaya_popup.time_scale_control.value()
        self.red_pitaya_popup.close()
        self.red_pitaya_popup = None
        self.controller.update_red_pitaya_parameters(self.red_pitaya_params)

    # ------------------ DEFAULTS ------------------ #

    @staticmethod
    def get_default_red_pitaya_parameters():
        return {"offset_1": default_parameters.CH1_OFFSET,
                "offset_2": default_parameters.CH2_OFFSET,
                "voltage_1": default_parameters.CH1_VOLTAGE,
                "voltage_2": default_parameters.CH2_VOLTAGE,
                "trigger_level": default_parameters.TRIGGER_LEVEL,
                "trigger_delay": default_parameters.TRIGGER_DELAY,
                "time_scale": default_parameters.TIME_SCALE}

    def set_default_pid_parameters(self):
        self.pid_control.kp_control.setValue(default_parameters.PID_KP)
        self.pid_control.ki_control.setValue(default_parameters.PID_KI)
        self.pid_control.kd_control.setValue(default_parameters.PID_KD)
        self.pid_control.lock_offset_control.setValue(default_parameters.PID_OFFSET)

    def set_default_hmp_parameters(self):
        self.hmp_control.laser_checkbox.setChecked(default_parameters.HMP_LASER_IS_ON)
        self.hmp_control.laser_current_control.setValue(default_parameters.HMP_LASER_CURRENT)
        self.hmp_control.halogen_checkbox.setChecked(default_parameters.HMP_HALOGEN_IS_ON)
        self.hmp_control.halogen_voltage_control.setValue(default_parameters.HMP_HALOGEN_VOLTAGE)

    def disable_hmp(self):
        self.hmp_control.laser_checkbox.setEnabled(False)
        self.hmp_control.laser_current_control.setEnabled(False)
        self.hmp_control.halogen_checkbox.setEnabled(False)
        self.hmp_control.halogen_voltage_control.setEnabled(False)

        self.pid_control.start_lock_button.setEnabled(False)
        self.pid_control.kp_control.setEnabled(False)
        self.pid_control.ki_control.setEnabled(False)
        self.pid_control.kd_control.setEnabled(False)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app: App):
        super().__init__()
        self.app = app
        self.main_container = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main_container)

        self.setWindowTitle("Cavity Lock")
        self.setGeometry(100, 100, 1600, 800)
        self.showMaximized()

        self.layout = QtWidgets.QHBoxLayout(self.main_container)

        self.plot_frame = MatplotlibContainer(self.main_container, self.app)
        self.layout.addWidget(self.plot_frame)

        self.buttons_container = SidePanel(self.main_container)
        self.layout.addWidget(self.buttons_container)

    def closeEvent(self, event):
        self.app.controller.stop()
        event.accept()


class MatplotlibContainer(QtWidgets.QWidget):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.master = master
        self.layout = QtWidgets.QVBoxLayout(self)

        self.title = QtWidgets.QLabel("", self)
        self.title.setFont(QtGui.QFont("Helvetica", 20, QtGui.QFont.Weight.Bold))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.title)

        self.fig = Figure(figsize=(16, 11), dpi=100)
        axes = self.fig.subplots(2, 1, sharex="all")
        self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        self.axes = {"transmission": axes[0], "rubidium": axes[1]}

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.toolbar)

        self.animation = animation.FuncAnimation(self.fig, self.plot_data, interval=50,
                                                 init_func=self.setup_plot, cache_frame_data=False,
                                                 blit=True)

    def plot_data(self, _):
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
                            self.axes["rubidium"].scatter([], [], c='r'),
                            self.axes["rubidium"].scatter([], [], c='g')]

        self.axes["rubidium"].set_ylim(-0.1, 1.1)

        return *transmission_artists, *rubidium_artists

    def add_2nd_figure(self, x_label, y_label):
        self.figure_2 = Figure(figsize=(16, 5), dpi=100)
        axes = self.figure_2.subplots(1, 1)
        self.figure_2.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        axes.set_xlabel(x_label)
        axes.set_ylabel(y_label)
        axes.grid()
        axes.plot([], [])
        self.axes["figure_2"] = axes

        self.canvas_2 = FigureCanvasQTAgg(self.figure_2)
        self.layout.addWidget(self.canvas_2)
        self.layout.addWidget(self.toolbar)

    def remove_2nd_figure(self):
        self.layout.removeWidget(self.canvas_2)
        self.canvas_2.close()
        self.canvas_2 = None
        self.figure_2 = None

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
        self.title.setText(title or "")
        self.plot_transmission_fit(x_axis, transmission_fit, x_0)
        self.plot_rubidium_peaks(rubidium_peaks, selected_peak)

    def remove_fit(self):
        self.title.setText("Error")

    def plot_2nd_figure(self, x_axis, signal):
        lines = self.axes["figure_2"].get_lines()
        lines[0].set_data(x_axis, signal)


class SidePanel(QtWidgets.QWidget):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.general_controls = GeneralControls(self)
        self.layout.addWidget(self.general_controls)

        separator = QtWidgets.QFrame(self)
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.layout.addWidget(separator)

        self.pid_control = PidControl(self)
        self.layout.addWidget(self.pid_control)

        separator = QtWidgets.QFrame(self)
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.layout.addWidget(separator)

        self.hmp_control = HmpControl(self)
        self.layout.addWidget(self.hmp_control)

        separator = QtWidgets.QFrame(self)
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.layout.addWidget(separator)

        self.connection_panel = ConnectionPanel(self)
        self.layout.addWidget(self.connection_panel)

        # self.v_spacer = QtWidgets.QSpacerItem(self.width(), 450)
        # self.layout.addItem(self.v_spacer)

    def disable_hmp(self):
        self.hmp_control.laser_checkbox.setEnabled(False)
        self.hmp_control.laser_current_control.setEnabled(False)
        self.hmp_control.halogen_checkbox.setEnabled(False)
        self.hmp_control.halogen_voltage_control.setEnabled(False)

        self.pid_control.start_lock_button.setEnabled(False)
        self.pid_control.kp_control.setEnabled(False)
        self.pid_control.ki_control.setEnabled(False)
        self.pid_control.kd_control.setEnabled(False)


class GeneralControls(QtWidgets.QWidget):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.popup = None

        self.layout = QtWidgets.QGridLayout(self)

        self.lock_error_button = QtWidgets.QPushButton("Show Error", self)
        self.layout.addWidget(self.lock_error_button, 0, 0)
        self.lock_error_button.setEnabled(False)
        self.calibrate_fit = QtWidgets.QPushButton("Calibrate Fit", self)
        self.layout.addWidget(self.calibrate_fit, 0, 1)
        self.select_peak = QtWidgets.QPushButton("Select Peak", self)
        self.layout.addWidget(self.select_peak, 1, 0)
        self.red_pitaya_panel = QtWidgets.QPushButton("RedPitaya", self)
        self.layout.addWidget(self.red_pitaya_panel, 1, 1)


class HmpControl(QtWidgets.QWidget):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.layout = QtWidgets.QGridLayout(self)

        self.device_control_title = QtWidgets.QLabel("Device Control", self)
        self.device_control_title.setFont(QtGui.QFont("Helvetica", 16, QtGui.QFont.Weight.Bold))
        self.device_control_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.device_control_title, 0, 0, 1, 2)

        start, end = parameter_bounds.HMP_LASER_CURRENT_BOUNDS
        self.laser_checkbox = QtWidgets.QCheckBox("Laser[current]:", self)
        self.layout.addWidget(self.laser_checkbox, 2, 0)
        self.laser_current_control = QtWidgets.QDoubleSpinBox(self)
        self.laser_current_control.setRange(start, end)
        self.laser_current_control.setSingleStep(0.01)
        self.layout.addWidget(self.laser_current_control, 2, 1)

        start, end = parameter_bounds.HMP_HALOGEN_VOLTAGE_BOUNDS
        self.halogen_checkbox = QtWidgets.QCheckBox("Halogen[voltage]:", self)
        self.layout.addWidget(self.halogen_checkbox, 3, 0)
        self.halogen_voltage_control = QtWidgets.QDoubleSpinBox(self)
        self.halogen_voltage_control.setRange(start, end)
        self.halogen_voltage_control.setSingleStep(0.1)
        self.layout.addWidget(self.halogen_voltage_control, 3, 1)


class PidControl(QtWidgets.QWidget):
    def __init__(self, master):
        super().__init__(master)
        self.layout = QtWidgets.QGridLayout(self)

        # ------------------ ROW 0 ------------------ #
        self.pid_controls_title = QtWidgets.QLabel("PID Controls", self)
        self.pid_controls_title.setFont(QtGui.QFont("Helvetica", 16, QtGui.QFont.Weight.Bold))
        self.pid_controls_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.pid_controls_title, 0, 0, 1, 6)

        # ------------------ ROW 1 ------------------ #
        self.kp_label = QtWidgets.QLabel("P:", self)
        self.layout.addWidget(self.kp_label, 1, 0)
        self.kp_control = QtWidgets.QDoubleSpinBox(self)
        self.kp_control.setRange(0, 10)
        self.kp_control.setSingleStep(0.1)
        self.layout.addWidget(self.kp_control, 1, 1)

        self.ki_label = QtWidgets.QLabel("I:", self)
        self.layout.addWidget(self.ki_label, 1, 2)
        self.ki_control = QtWidgets.QDoubleSpinBox(self)
        self.ki_control.setRange(0, 10)
        self.ki_control.setSingleStep(0.1)
        self.layout.addWidget(self.ki_control, 1, 3)

        self.kd_label = QtWidgets.QLabel("D:", self)
        self.layout.addWidget(self.kd_label, 1, 4)
        self.kd_control = QtWidgets.QDoubleSpinBox(self)
        self.kd_control.setRange(0, 10)
        self.kd_control.setSingleStep(0.1)
        self.layout.addWidget(self.kd_control, 1, 5)

        # ------------------ ROW 2 ------------------ #
        start, end = parameter_bounds.PID_OFFSET_BOUNDS
        self.lock_offset_label = QtWidgets.QLabel("Lock Offset:", self)
        self.layout.addWidget(self.lock_offset_label, 2, 0, 1, 3)
        self.lock_offset_control = QtWidgets.QDoubleSpinBox(self)
        self.lock_offset_control.setRange(start, end)
        self.lock_offset_control.setSingleStep(0.5)
        self.layout.addWidget(self.lock_offset_control, 2, 3, 1, 3)

        # ------------------ ROW 3 ------------------ #
        self.start_lock_button = QtWidgets.QPushButton("Start Lock", self)
        self.start_lock_button.setCheckable(True)
        self.layout.addWidget(self.start_lock_button, 3, 0, 1, 6)


class ConnectionPanel(QtWidgets.QWidget):
    def __init__(self, master):
        super().__init__(master)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.socket_label = QtWidgets.QLabel("Socket Connection:", self)
        self.layout.addWidget(self.socket_label)

        self.connection_led = self.get_connection_circle()
        self.layout.addWidget(self.connection_led)

        self.h_spacer = QtWidgets.QSpacerItem(150, 10)
        self.layout.addItem(self.h_spacer)

    def get_connection_circle(self):
        scene = QtWidgets.QGraphicsScene()
        circle_item = QtWidgets.QGraphicsEllipseItem(0, 0, 10, 10)
        circle_item.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
        scene.addItem(circle_item)

        view = QtWidgets.QGraphicsView(scene, self)
        view.setStyleSheet("border: none;")
        return view

    def set_connection_led_status(self, is_connected):
        color = QtGui.QColor(0, 255, 0) if is_connected else QtGui.QColor(255, 0, 0)
        self.connection_led.scene().items()[0].setBrush(QtGui.QBrush(color))


class RedPitayaControlPanel(QtWidgets.QDialog):
    def __init__(self, master, params, update_callback):
        super().__init__(master)
        self.params = params
        self.setWindowTitle("Red Pitaya Control Panel")
        master_geometry = master.frameGeometry()
        width = 600
        height = 300
        self.setGeometry(master_geometry.width()//2-width//2, master_geometry.height()//2-height//2, width, height)
        self.layout = QtWidgets.QGridLayout(self)

        # ------------------ ROW 0 ------------------ #
        self.channel_1_label = QtWidgets.QLabel("Channel 1", self)
        self.layout.addWidget(self.channel_1_label, 0, 1)
        self.channel_2_label = QtWidgets.QLabel("Channel 2", self)
        self.layout.addWidget(self.channel_2_label, 0, 2)

        # ------------------ ROW 1 ------------------ #
        start, end = parameter_bounds.RED_PITAYA_OFFSET_BOUNDS
        self.offset_label = QtWidgets.QLabel("Offset:", self)
        self.layout.addWidget(self.offset_label, 1, 0)

        self.offset_control_1 = QtWidgets.QDoubleSpinBox(self)
        self.offset_control_1.setRange(start, end)
        self.offset_control_1.setSingleStep(0.1)
        self.offset_control_1.setValue(params["offset_1"])
        self.layout.addWidget(self.offset_control_1, 1, 1)

        self.offset_control_2 = QtWidgets.QDoubleSpinBox(self)
        self.offset_control_2.setRange(start, end)
        self.offset_control_2.setSingleStep(0.1)
        self.offset_control_2.setValue(params["offset_2"])
        self.layout.addWidget(self.offset_control_2, 1, 2)

        # ------------------ ROW 2 ------------------ #
        start, end = parameter_bounds.RED_PITAYA_VOLTAGE_BOUNDS
        self.voltage_label = QtWidgets.QLabel("Voltage:", self)
        self.layout.addWidget(self.voltage_label, 2, 0)

        self.voltage_control_1 = QtWidgets.QDoubleSpinBox(self)
        self.voltage_control_1.setRange(start, end)
        self.voltage_control_1.setSingleStep(0.1)
        self.voltage_control_1.setValue(params["voltage_1"])
        self.layout.addWidget(self.voltage_control_1, 2, 1)

        self.voltage_control_2 = QtWidgets.QDoubleSpinBox(self)
        self.voltage_control_2.setRange(start, end)
        self.voltage_control_2.setSingleStep(0.1)
        self.voltage_control_2.setValue(params["voltage_2"])
        self.layout.addWidget(self.voltage_control_2, 2, 2)

        # ------------------ ROW 4 ------------------ #
        self.trigger_level_label = QtWidgets.QLabel("Level", self)
        self.layout.addWidget(self.trigger_level_label, 4, 1)
        self.trigger_delay_label = QtWidgets.QLabel("Delay", self)
        self.layout.addWidget(self.trigger_delay_label, 4, 2)

        # ------------------ ROW 5 ------------------ #
        start, end = parameter_bounds.RED_PITAYA_TRIGGER_LEVEL_BOUNDS
        self.trigger_label = QtWidgets.QLabel("Trigger:", self)
        self.layout.addWidget(self.trigger_label, 5, 0)

        self.trigger_control_1 = QtWidgets.QDoubleSpinBox(self)
        self.trigger_control_1.setRange(start, end)
        self.trigger_control_1.setSingleStep(0.1)
        self.trigger_control_1.setValue(params["trigger_level"])
        self.layout.addWidget(self.trigger_control_1, 5, 1)

        self.trigger_control_2 = QtWidgets.QDoubleSpinBox(self)
        self.trigger_control_2.setRange(start, end)
        self.trigger_control_2.setSingleStep(0.1)
        self.trigger_control_2.setValue(params["trigger_delay"])
        self.layout.addWidget(self.trigger_control_2, 5, 2)

        # ------------------ ROW 7 ------------------ #
        self.time_scale_label = QtWidgets.QLabel("Time Scale [ms]:", self)
        self.layout.addWidget(self.time_scale_label, 7, 0)

        self.time_scale_control = QtWidgets.QDoubleSpinBox(self)
        self.time_scale_control.setRange(0, 1)
        self.time_scale_control.setSingleStep(0.05)
        self.time_scale_control.setValue(params["time_scale"])
        self.layout.addWidget(self.time_scale_control, 7, 1, 1, 2)

        # ------------------ ROW 8 ------------------ #
        buttons = QtWidgets.QDialogButtonBox.StandardButton.Cancel | QtWidgets.QDialogButtonBox.StandardButton.Ok
        self.button_box = QtWidgets.QDialogButtonBox(self)
        self.button_box.setStandardButtons(buttons)
        self.button_box.setContentsMargins(10, 10, 10, 10)
        self.layout.addWidget(self.button_box, 8, 0, 1, 3)
        # noinspection PyUnresolvedReferences
        self.button_box.accepted.connect(update_callback)
        # noinspection PyUnresolvedReferences
        self.button_box.rejected.connect(self.close)
