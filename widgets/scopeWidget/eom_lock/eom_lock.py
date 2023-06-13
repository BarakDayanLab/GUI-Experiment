import os
import sys
import time
import traceback

import numpy
import numpy as np
import tempfile
#import numpy as np

from PyQt5 import uic
from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import QApplication

import matplotlib.pyplot as plt

from widgets.scopeWidget.scope import Scope_GUI

# TODO:
# 1) Print on UI the RedPitaya address
# 2) Ch1/Ch2 fixed voltages


# We have the AWG send a modulating signal to the EOM
# The EOM has a tendency to drift
class EOMLockGUI(Scope_GUI):
    MOUNT_DRIVE = "U:\\"
    OUTPUT_CHANNEL = 1  # There is 1 and 2 for the Red Pitaya
    DBG_CHANNEL = 2
    INPUT_CHANNEL1 = 1
    INPUT_CHANNEL2 = 2

    def __init__(self, parent=None, ui=None, debugging=False, simulation=True):
        self.lock_on = False
        self.x = 3.5
        self.yy0 = 0
        self.yy1_average = np.zeros(1)
        self.step = None  # Gets overriden by UI anyways...
        self.weight = None  # Gets overriden by UI anyways...
        self.er_threshold = None  # Gets overriden by UI anyways...
        self.offset = None  # Gets overriden by UI anyways... -0.001
        self.flag = 1
        self.iteration = 0
        self.prev_ns = time.time_ns()
        self.nudging = None  # Flag for one-time nudging of the step parameter

        # For Debug purposes - scan DC amplitudes
        self.sweep_mode = True
        self.svolts_delta = 0.025
        self.svolts = -4.5
        self.extintion_ratio_vec = []
        self.min_vec = []
        self.out_vec = []

        if parent is not None:
            self.parent = parent

        # Set folders and files
        self.log_file = os.path.join(self.MOUNT_DRIVE, "another_folder")
        self.temp_file = path = tempfile.gettempdir()

        # RP first run flag is required to set plotting and channels
        self.red_pitaya_first_run = True

        # Set thread pool
        if __name__ == "__main__":
            self.threadpool = QThreadPool()
            print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        # Get the UI file for EOM lock - the generic frame
        ui = os.path.join(os.path.dirname(__file__), "eomLockWidgetGUI.ui") if ui is None else ui

        self.red_pitaya_host = CONFIG["red-pitaya-host"]
        super().__init__(Parent=parent, ui=ui, debugging=debugging, simulation=simulation, RedPitayaHost=self.red_pitaya_host)


        # Add outputs control UI
        self.outputsFrame = self.frame_4
        ui_outputs = os.path.join(os.path.dirname(__file__), ".\\eomLockCustomControl.ui")
        uic.loadUi(ui_outputs, self.frame_4)  # place outputs in frame 4

        # Wait 1 sec - allow the UI to load before we connect and read its values
        time.sleep(1.0)

        # Bind events of UI controls to our update functions
        self.connectOutputsButtonsAndSpinboxes()

        # Update the default lock settings based on the UI defaults
        self.update_step_and_weight()


    def configure_input_channels(self):
        self.rp.set_inputState(self.INPUT_CHANNEL1, True)
        self.rp.set_inputState(self.INPUT_CHANNEL2, True)
        self.rp.set_inputAcDcCoupling(self.INPUT_CHANNEL1, "DC")
        self.rp.set_inputAcDcCoupling(self.INPUT_CHANNEL2, "DC")

    def configure_output_channels(self):
        # Set channel 1
        self.rp.set_outputGain(self.OUTPUT_CHANNEL, 'X5', True)
        self.rp.set_outputImpedance(self.OUTPUT_CHANNEL, '50_OHM', verbose=True)  # 50_OHM, HI_Z
        self.rp.set_outputFunction(self.OUTPUT_CHANNEL, 8)  # 0=SINE 1=SQUARE 5=DC
        self.rp.set_outputAmplitude(self.OUTPUT_CHANNEL, abs(self.svolts))
        self.rp.set_outputOffset(self.OUTPUT_CHANNEL, 0)
        self.rp.set_outputState(self.OUTPUT_CHANNEL, True)

        # Set channel 2 - debug
        self.rp.set_outputGain(self.DBG_CHANNEL, 'X5', True)
        self.rp.set_outputImpedance(self.DBG_CHANNEL, '50_OHM', verbose=True)  # 50_OHM, HI_Z
        self.rp.set_outputFunction(self.DBG_CHANNEL, 8)  # 0=SINE 1=SQUARE 5=DC 8=DC_NEG
        self.rp.set_outputAmplitude(self.DBG_CHANNEL, abs(self.svolts))
        self.rp.set_outputOffset(self.DBG_CHANNEL, 0)
        self.rp.set_outputState(self.DBG_CHANNEL, True)

    # Bind the GUI elements in the Generic frame (common to all lockers)
    def connect_custom_ui_controls(self):
        self.checkBox_ch1_lines.clicked.connect(self.chns_update)
        self.checkBox_ch2_lines.clicked.connect(self.chns_update)
        # Connect the trigger related combo boxes - Channel and Sweep
        self.comboBox_triggerSource.currentTextChanged.connect(self.updateTriggerSource)
        self.comboBox_triggerSweep.currentTextChanged.connect(self.updateTriggerSweep)
        self.comboBox_triggerSlope.currentTextChanged.connect(self.updateTriggerSlope)

        self.comboBox_channel1Coupling.currentTextChanged.connect(self.updateChannelCoupling)
        self.comboBox_channel2Coupling.currentTextChanged.connect(self.updateChannelCoupling)

    # Bind the GUI elements in the Custom frame - "outputsFrame" (top-right)
    def connectOutputsButtonsAndSpinboxes(self):
        # Get Step and Weight parameters
        self.outputsFrame.doubleSpinBox_Step.valueChanged.connect(self.update_step_and_weight)
        self.outputsFrame.doubleSpinBox_Weight.valueChanged.connect(self.update_step_and_weight)
        self.outputsFrame.doubleSpinBox_Threshold.valueChanged.connect(self.update_step_and_weight)
        self.outputsFrame.doubleSpinBox_Offset.valueChanged.connect(self.update_step_and_weight)

        # Output buttons
        self.outputsFrame.pushButton_StartLock.clicked.connect(self.toggle_lock)
        self.outputsFrame.pushButton_Reset.clicked.connect(self.reset_lock)
        self.outputsFrame.pushButton_nudgeUp.clicked.connect(self.nudge_up)
        self.outputsFrame.pushButton_nudgeDown.clicked.connect(self.nudge_down)

        # Connect checkboxes that enable/disable the output channels
        self.outputsFrame.checkBox_ch1OuputState.stateChanged.connect(self.updateOutputChannels)
        self.outputsFrame.checkBox_ch2OuputState.stateChanged.connect(self.updateOutputChannels)

    # Zero the data buffers upon averaging params change (invoked by super-class)
    def averaging_parameters_updated(self):
        self.channel1_data = np.zeros((self.Avg_num[0], self.signalLength))  # Place holder
        self.channel2_data = np.zeros((self.Avg_num[1], self.signalLength))  # Place holder

    # Updates the step/weight params that affect the lock mechanism
    def update_step_and_weight(self):
        self.step = float(self.outputsFrame.doubleSpinBox_Step.value())
        self.weight = float(self.outputsFrame.doubleSpinBox_Weight.value())
        self.er_threshold = float(self.outputsFrame.doubleSpinBox_Threshold.value())
        self.offset = float(self.outputsFrame.doubleSpinBox_Offset.value())

    def updateOutputChannels(self):
        self.changedOutputs = True
        # self.rp.set_outputFunction(output=1, function=str(self.outputsFrame.comboBox_ch1OutFunction.currentText()))
        # self.rp.set_outputFunction(output=2, function=str(self.outputsFrame.comboBox_ch2OutFunction.currentText()))
        # self.rp.set_outputAmplitude(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutAmp.value()))
        # self.rp.set_outputAmplitude(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutAmp.value()))
        # self.rp.set_outputFrequency(output=1, freq=float(self.outputsFrame.doubleSpinBox_ch1OutFreq.value()))
        # self.rp.set_outputFrequency(output=2, freq=float(self.outputsFrame.doubleSpinBox_ch2OutFreq.value()))
        # self.rp.set_outputOffset(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutOffset.value()))
        # self.rp.set_outputOffset(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutOffset.value()))
        self.rp.set_outputState(output=1, state=bool(self.outputsFrame.checkBox_ch1OuputState.checkState()))
        self.rp.set_outputState(output=2, state=bool(self.outputsFrame.checkBox_ch2OuputState.checkState()))
        self.rp.updateParameters()

    # Find the drop/raise points
    def find_fall_or_rise(self, signal):
        signal = np.array(signal)

        min = signal.min()
        max = signal.max()
        delta = (max-min)*0.85/2.0

        # Iterate over all points and calc their delta
        p = np.diff(signal)

        i = np.argmax(abs(p)>delta)
        return i

    def update_scope(self, data, parameters):

        if self.red_pitaya_first_run:
            self.updatePlotDisplay()  # Update the rest of the RedPitaya settings based on the UI
            self.setInverseChns()
            self.showHideParametersWindow()
            self.chns_update()  # Sets new_parameters to True - so we "fake" parameters change for the first run
            self.updateOutputChannels()  # Sets flag so we "fake" as if output channels were changed
            self.red_pitaya_first_run = False
            # Configure Red Pitaya Output channel
            self.configure_input_channels()
            self.configure_output_channels()

        # Decide to redraw if (a) New parameters are in -or- (b) Channels updated
        # (if the outputs were changed, no need to redraw)
        redraw = (parameters['new_parameters'] or self.CHsUpdated) and not self.changedOutputs
        if redraw:
            self.scope_parameters = parameters  # keep all the parameters. we need them.
            self.CHsUpdated = False
        else:
            pass

        self.changedOutputs = False

        # Insert new data from channels to the corresponding averaging array
        self.channel1_data[self.Avg_indx % self.Avg_num[0]] = data[0]
        self.channel2_data[self.Avg_indx % self.Avg_num[1]] = data[1]

        self.Avg_indx = self.Avg_indx + 1

        self.changedOutputs = False

        # Check signal
        drop_rise_point = self.find_fall_or_rise(data[0])

        # ---------------- Average data  ----------------
        # Calculate average data:
        Avg_data = []
        if self.checkBox_ch1_lines.isChecked():
            self.channel1_avg_data = np.average(self.channel1_data, axis=0)
            Avg_data = Avg_data + [self.channel1_avg_data]
        if self.checkBox_ch2_lines.isChecked():
            self.channel2_avg_data = np.average(self.channel2_data, axis=0)
            Avg_data = Avg_data + [self.channel2_avg_data]
            # Add output line to the graph
            #buffer = np.full((1024,), self.x)
            #Avg_data = Avg_data + [buffer]

        # Text box to be printed in lower right corner
        text_box_string = "EOM Lock"

        time_scale = float(self.scope_parameters['OSC_TIME_SCALE']['value'])
        indx_to_time = float(10 * time_scale / self.scope_parameters['OSC_DATA_SIZE']['value'])
        num_of_samples = int(self.scope_parameters['OSC_DATA_SIZE']['value'])
        # Create an evenly spaced array for the x-axis based on number of samples and time scale
        x_axis = np.linspace(0, time_scale * 10, num=num_of_samples)
        x_ticks = np.arange(x_axis[0], x_axis[-1], time_scale)
        x_axis_units = '[ms]'

        y_scale = [float(self.doubleSpinBox_VtoDiv_ch1.text()), float(self.doubleSpinBox_VtoDiv_ch2.text())]
        y_offset = [float(self.doubleSpinBox_VOffset_ch1.text()), float(self.doubleSpinBox_VOffset_ch2.text())]
        # Create two array of ticks, for the two scales of the two channels
        y_ticks = [np.arange(y_offset[i] - y_scale[i] * 5, y_offset[i] + y_scale[i] * 5, y_scale[i])
                   for i in range(len(y_scale))]
        autoscale = self.checkBox_plotAutoscale.isChecked()

        # --------- plot ---------
        # Prepare data for display:
        labels = ["CH1 - channel 1 description", "CH2 - channel 2 description"]
        try:
            self.widgetPlot.plot_Scope(x_axis, Avg_data,
                                       autoscale=autoscale,
                                       redraw=redraw,
                                       labels=labels,
                                       x_ticks=x_ticks,
                                       y_ticks=y_ticks,
                                       #aux_plotting_func = self.widgetPlot.plot_Scatter,
                                       #scatter_y_data=np.concatenate([Avg_data[0][Rb_peaks], Avg_data[1][Cavity_peak]]),
                                       #scatter_x_data=np.concatenate([x_axis[Rb_peaks], x_axis[Cavity_peak]]),
                                       #mark_peak = self.selectedPeaksXY,
                                       text_box=text_box_string)
        except Exception as e:
            tb = traceback.format_exc()
            print(tb)

        # --------- Lock -----------
        self.perform_lock()

        # -------- Save Data  --------:
        if self.checkBox_saveData.isChecked():
            self.saveCurrentDataClicked()

    # We toggle the state and change the button text
    # Note: we deliberately don't zero the DC out as we want to leave it the way it was
    #       when we stopped the locking
    def toggle_lock(self):
        if self.lock_on:
            self.outputsFrame.pushButton_StartLock.setText('Start Lock')
            self.outputsFrame.label_LockSettings.setText("EOM Lock Settings [Lock OFF]")
            self.rp.print('Lock stopped.', 'blue')
        else:
            self.outputsFrame.pushButton_StartLock.setText('Stop Lock')
            self.outputsFrame.label_LockSettings.setText("EOM Lock Settings [Lock ON]")
            self.rp.print('Lock started.', 'blue')

        self.lock_on = not self.lock_on

    def reset_lock(self):
        pass

    def nudge_up(self):
        self.nudging = 'up'

    def nudge_down(self):
        self.nudging = 'down'

    # Insert new value into an averaging bin and return the average
    def average_yy1(self, yy1):
        self.yy1_average[:-1] = self.yy1_average[1:]
        self.yy1_average[-1] = yy1
        avg = np.average(self.yy1_average)
        return avg

    def get_milliseconds_delta(self):
        ns = time.time_ns()
        delta = (ns - self.prev_ns) / 1_000_000
        self.prev_ns = ns
        return round(delta)

    def perform_lock(self):

        self.iteration = self.iteration + 1
        if self.iteration % 5 > 0:
            return

        # Find min/max
        min = self.channel1_avg_data.min()-self.offset
        max = self.channel1_avg_data.max()-self.offset
        if min < 0:
            min = 0.001  # Avoid having extinction rate as INF
        if max < 0:
            max = 0

        # Calculate extinction ratio and yy1
        extinction_ratio = max/min
        yy1 = self.average_yy1(extinction_ratio)

        # Handle threshold
        if extinction_ratio > self.er_threshold:
            style = "background-color: green;border: 1px solid black;"
        else:
            style = "background-color: white;border: 0px solid black;"

        delta_millis = self.get_milliseconds_delta()
        sample_rate_khz = 1/delta_millis*1000

        # Output the extinction ratio to the GUI
        if not self.sweep_mode:
            txt = "ER: %.2f  V: %.2f  yy1: %.2f  LR: %.1f" % (extinction_ratio, self.x, yy1, sample_rate_khz)
        else:
            txt = "ER: %.2f  V: %.2f  yy1: %.2f  SW: %.1f" % (extinction_ratio, self.x, yy1, self.svolts)
        self.outputsFrame.label_ExtinctionRatio.setText(txt)
        self.outputsFrame.label_ExtinctionRatio.setStyleSheet(style)

        # If we're locked - re-calc output and send it out
        if self.lock_on:
            # Should we change the sign of the step?
            if yy1 < self.yy0:
                self.flag = -self.flag

            if self.nudging == 'up':
                weight = self.weight
                self.nudging = None
            elif self.nudging == 'down':
                weight = -self.weight
                self.nudging = None
            else:
                weight = 1.0

            # Re-calc output
            self.x = self.x + self.step * weight * self.flag

            self.nudging = False

            # Defend output from outliers
            if self.x >= 5.0:
                self.x = 4.5
            elif self.x <= 0:
                self.x = 0.001

            # Handle Sweep mode
            if self.sweep_mode:
                self.sweep(extinction_ratio)
            else:
                # Set the RP output amplitude
                self.rp.set_outputAmplitude(self.OUTPUT_CHANNEL, self.x)
                self.rp.set_outputAmplitude(self.DBG_CHANNEL, self.x)

            self.yy0 = yy1

    def sweep(self, extinction_ratio):
        # Increment volts
        self.svolts = self.svolts + self.svolts_delta

        # Set the output accordingly
        self.rp.set_outputDCAmplitude(self.OUTPUT_CHANNEL, self.svolts)
        self.rp.set_outputDCAmplitude(self.DBG_CHANNEL, self.svolts)

        self.extintion_ratio_vec.append(extinction_ratio)
        self.min_vec.append(min)
        self.out_vec.append(self.svolts)

        # Change the sign of the delta
        self.svolts_delta = -self.svolts_delta if abs(self.svolts) > 4.5 else self.svolts_delta

    # Zero the data buffers upon averaging params change (invoked by super-class)
    def averaging_parameters_updated(self):
        self.channel1_data = np.zeros((self.Avg_num[0], self.signalLength))  # Place holder
        self.channel2_data = np.zeros((self.Avg_num[1], self.signalLength))  # Place holder
        pass

    # Handle update of output channels (from UI) - set flag and update Red Pitaya
    def updateOutputChannels(self):
        # TODO: add hold-update to rp
        self.changedOutputs = True
        # self.rp.set_outputFunction(output=1, function=str(self.outputsFrame.comboBox_ch1OutFunction.currentText()))
        # self.rp.set_outputFunction(output=2, function=str(self.outputsFrame.comboBox_ch2OutFunction.currentText()))
        # self.rp.set_outputAmplitude(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutAmp.value()))
        # self.rp.set_outputAmplitude(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutAmp.value()))
        # self.rp.set_outputFrequency(output=1, freq=float(self.outputsFrame.doubleSpinBox_ch1OutFreq.value()))
        # self.rp.set_outputFrequency(output=2, freq=float(self.outputsFrame.doubleSpinBox_ch2OutFreq.value()))
        # self.rp.set_outputOffset(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutOffset.value()))
        # self.rp.set_outputOffset(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutOffset.value()))
        self.rp.set_outputState(output=1, state=bool(self.outputsFrame.checkBox_ch1OuputState.checkState()), verbose=True)
        self.rp.set_outputState(output=2, state=bool(self.outputsFrame.checkBox_ch2OuputState.checkState()), verbose=True)

        # Update the Red Pitaya that channels have changed
        self.rp.updateParameters()

if __name__ == "__main__":
    app = QApplication([])
    login = os.getlogin()
    simulation = False  # This is only relevant for PGC-Widget

    RED_PITAYA_HOST_125 = "rp-f08c36.local"  # Small one (125)
    RED_PITAYA_HOST_250 = "rp-ffff3e.local"  # Large one (250)

    CONFIG = {
        "login": login,
        "red-pitaya-host": RED_PITAYA_HOST_125 if login == 'drorg' else RED_PITAYA_HOST_250
    }
    window = EOMLockGUI(simulation=simulation, debugging=True)
    window.show()
    app.exec_()
    sys.exit(app.exec_())
