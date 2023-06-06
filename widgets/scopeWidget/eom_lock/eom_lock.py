import os
import sys
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


# We have the AWG send a modulating signal to the EOM
# The EOM has a tendency to drift
class EOMLockGUI(Scope_GUI):
    MOUNT_DRIVE = "U:\\"
    #RED_PITAYA_HOST = "rp-f08c36.local"  # 125
    RED_PITAYA_HOST = "rp-ffff3e.local"  # 250
    OUTPUT_CHANNEL = 1  # There is 1 and 2 for the Red Pitaya
    DBG_CHANNEL = 2
    SINE_FUNC = 0
    SQUARE_FUNC = 1
    DC_FUNC = 5

    def __init__(self, parent=None, ui=None, debugging=False, simulation=True):
        self.lockOn = True
        self.x = 0
        self.prev_extinction_rate = 0
        self.step = 0.2
        self.weight = 1.0
        self.flag = 1
        self.offset = -0.013

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

        super().__init__(Parent=parent, ui=ui, debugging=debugging, simulation=simulation, RedPitayaHost=self.RED_PITAYA_HOST)

        # Add outputs control UI
        self.outputsFrame = self.frame_4
        ui_outputs = os.path.join(os.path.dirname(__file__), ".\\eomLockCustomControl.ui")
        uic.loadUi(ui_outputs, self.frame_4)  # place outputs in frame 4
        self.connectOutputsButtonsAndSpinboxes()

        self.fig = plt.figure()
        self.y_axis=[]


    def configure_input_channels(self):
        self.rp.set_ac_dc_coupling_state(1, "DC_COUPLING")
        self.rp.set_ac_dc_coupling_state(2, "DC_COUPLING")
        pass

    def configure_output_channels(self):
        # An example of sending out a SQUARE_FUNC:
        # self.rp.set_outputState(self.OUTPUT_CHANNEL, True)
        # self.rp.set_outputFunction(self.OUTPUT_CHANNEL, self.SQUARE_FUNC)  # 0=SINE 1=SQUARE 5=DC
        # self.rp.set_outputTrigger(self.OUTPUT_CHANNEL, 0)  # Internal Trigger
        # self.rp.set_outputAmplitude(self.OUTPUT_CHANNEL, 0.8)
        # self.rp.set_outputFrequency(self.OUTPUT_CHANNEL, 1)  # 1 Hz

        if True:
            self.rp.set_outputState(self.OUTPUT_CHANNEL, True)
            self.rp.set_outputFunction(self.OUTPUT_CHANNEL, self.DC_FUNC)  # 0=SINE 1=SQUARE 5=DC
            self.rp.set_outputAmplitude(self.OUTPUT_CHANNEL, 0.8)

            self.rp.set_outputState(self.DBG_CHANNEL, True)
            self.rp.set_outputFunction(self.DBG_CHANNEL, self.DC_FUNC)  # 0=SINE 1=SQUARE 5=DC
            self.rp.set_outputAmplitude(self.DBG_CHANNEL, 0.6)

        pass

    def connect_custom_ui_controls(self):
        self.checkBox_ch1_lines.clicked.connect(self.chns_update)
        self.checkBox_ch2_lines.clicked.connect(self.chns_update)

    def connectOutputsButtonsAndSpinboxes(self):
        # Get Step and Weight parameters
        self.outputsFrame.doubleSpinBox_Step.valueChanged.connect(self.update_step_and_weight)
        self.outputsFrame.doubleSpinBox_Weight.valueChanged.connect(self.update_step_and_weight)

        # TODO: change the name of this checkbox... (or add another checkbox)
        self.outputsFrame.checkBox_ac_dc_OuputState.stateChanged.connect(self.udpateAcDcCoupling)

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
        pass

    def udpateAcDcCoupling(self):
        self.changedOutputs = True
        ac_dc_coupling = 0 if bool(self.outputsFrame.checkBox_ac_dc_OuputState.checkState()) else 1
        self.rp.set_ac_dc_coupling_state(channel=1, coupling=ac_dc_coupling)
        self.rp.set_ac_dc_coupling_state(channel=2, coupling=ac_dc_coupling)
        self.rp.updateParameters()

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

        # ---------------- Average data  ----------------
        # Calculate average data:
        Avg_data = []
        if self.checkBox_ch1_lines.isChecked():
            self.channel1_avg_data = np.average(self.channel1_data, axis=0)
            Avg_data = Avg_data + [self.channel1_avg_data]
        if self.checkBox_ch2_lines.isChecked():
            #self.channel2_avg_data = np.average(self.channel2_data, axis=0)
            #Avg_data = Avg_data + [self.channel2_avg_data]
            # Add output line to the graph
            buffer = np.full((1024,), self.x)
            Avg_data = Avg_data + [buffer]

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
            pass

        # --------- Lock -----------
        if self.lockOn:
            self.lock()

        # -------- Save Data  --------:
        if self.checkBox_saveData.isChecked():
            self.saveCurrentDataClicked()

    def lock(self):
        # Find the peaks - high and low
        min = self.channel1_data.min()-self.offset
        max = self.channel1_data.max()-self.offset

        if min < 0:
            min=0.01  # Avoid having extinction rate as INF
        if max < 0:
            max=0

        extinction_rate = max/min

        THRESHOLD = 1000

        if extinction_rate > THRESHOLD:
            pass
        elif extinction_rate < self.prev_extinction_rate:
            self.flag = -self.flag

        self.x = self.x + self.step * self.weight * self.flag

        if self.x >= 5.0:
            self.x = 5.0
        elif self.x <= -5.0:
            self.x = -5.0

        self.rp.set_outputAmplitude(self.OUTPUT_CHANNEL, self.x)
        self.rp.set_outputAmplitude(self.DBG_CHANNEL, self.x)

        self.prev_extinction_rate = extinction_rate

        self.outputsFrame.doubleSpinBox_extinctionRatio.value = self.x
        #self.outputsFrame.ExtinctionRatioLabel.setText(self.x)

        self.y_axis.append(extinction_rate)

        print(extinction_rate)
        # plt.plot(np.arange(0,len(self.y_axis)),self.y_axis)
        # plt.clf()

        pass

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
        self.rp.set_outputState(output=1, state=bool(self.outputsFrame.checkBox_ch1OuputState.checkState()))
        self.rp.set_outputState(output=2, state=bool(self.outputsFrame.checkBox_ch2OuputState.checkState()))

        # Update the Red Pitaya that channels have changed
        self.rp.updateParameters()

if __name__ == "__main__":
    app = QApplication([])
    simulation = False if os.getlogin() == 'drorg' else True

    window = EOMLockGUI(simulation=simulation, debugging=True)
    window.show()
    app.exec_()
    sys.exit(app.exec_())
