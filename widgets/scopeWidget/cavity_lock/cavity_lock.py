
from PyQt5 import uic
from scipy import optimize,spatial
from scipy.signal import find_peaks
# import vxi11 # https://github.com/python-ivi/python-vxi11
import os
import sys
import numpy as np
from PyQt5.QtWidgets import QApplication
import matplotlib
from PID import PID
from PyQt5.QtCore import QThreadPool
from functions.HMP4040Control import HMP4040Visa
_CONNECTION_ATTMPTS = 2
_HALOGEN_VOLTAGE_LIMIT = 12 # [VOLTS], 3.3 for red laser
_LASER_CURRENT_MAX = 0.4 # [AMPS]
_LASER_CURRENT_MIN = 0.02 # [AMPS]
_LASER_TYPICAL_VOLTAGE = 3 #[volts]

try:
    from functions.cavity_lock.cavity_lock import CavityLock
except:
    print("Run without calculate OD")
if matplotlib.get_backend() != 'Qt5Agg':
    matplotlib.use('Qt5Agg')

from widgets.scopeWidget.scope import Scope_GUI


class Cavity_lock_GUI(Scope_GUI):
    def __init__(self, Parent=None, ui=None,debugging = False, simulation=True):
        if Parent is not None:
            self.Parent = Parent

        self.listenForMouseClickCID = None
        self.pid = None
        self.lockOn = False
        self.outputOffset = (_LASER_CURRENT_MAX + _LASER_CURRENT_MIN) / 2  # [mAmps]; default. should be value of laser output when lock is started.
        self.changedOutputs = False # this keeps track of changes done to outputs. if this is true, no total-redraw will happen (although usually we would update scope after any change in RP)

        # ---------- Rb Peaks ----------
        self.selectedPeaksXY = None
        self.indx_to_freq = [0]

        # ----------- HMP4040 Control -----------
        self.HMP4040 = HMP4040Visa(port = 'ASRL7::INSTR')
        self.HMP4040.setOutput(4)

        # ----------- Velocity Intrument -----------
        # try:
        #     self.velocity = vxi11.Instrument("169.254.46.36", 'gpib0,1')
        #     idn = self.velocity.ask("*IDN?")
        #     if idn != 'NewFocus 6312 GT3063 H0.39 C0.39':
        #         print('could not connect to velocity. Check connections.')
        #     self.print_to_dialogue(idn, color = 'green')
        #     self.velocityWavelength = float(self.velocity.ask('WAVE?'))
        #     self.doubleSpinBox_velocityWavelength.setValue(self.velocityWavelength)
        #     self.doubleSpinBox_velocityWavelength.valueChanged.connect(self.updateVelocityWavelength)
        # except:
        #     self.print_to_dialogue('Could not connect to velocity.', color= 'red')
        if __name__ == "__main__":
            self.threadpool = QThreadPool()
            print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        super().__init__(Parent=Parent, ui=ui, debugging=debugging, simulation=simulation)
        # up to here, nothing to change.

        # Add outputs control UI
        self.outputsFrame=self.frame_4
        ui_outputs = os.path.join(os.path.dirname(__file__), "..\\outputsControl.ui")
        uic.loadUi(ui_outputs, self.frame_4) # place outputs in frame 4
        self.connectOutputsButtonsAndSpinboxes()

        # -- Set output voltage ---
        self.outputsFrame.doubleSpinBox_outVHalogen.setValue(_LASER_TYPICAL_VOLTAGE)

    def connectOutputsButtonsAndSpinboxes(self):
        # PID spniboxes
        self.outputsFrame.doubleSpinBox_P.valueChanged.connect(self.updatePID)
        self.outputsFrame.doubleSpinBox_I.valueChanged.connect(self.updatePID)
        self.outputsFrame.doubleSpinBox_D.valueChanged.connect(self.updatePID)

        # Output spinboxes & buttons
        self.outputsFrame.pushButton_StartLock.clicked.connect(self.toggleLock)
        self.outputsFrame.pushButton_selectPeak.clicked.connect(self.scopeListenForMouseClick)

        self.outputsFrame.comboBox_ch1OutFunction.currentIndexChanged.connect(self.updateOutputChannels)
        self.outputsFrame.comboBox_ch2OutFunction.currentIndexChanged.connect(self.updateOutputChannels)
        self.outputsFrame.doubleSpinBox_ch1OutAmp.valueChanged.connect(self.updateOutputChannels)
        self.outputsFrame.doubleSpinBox_ch2OutAmp.valueChanged.connect(self.updateOutputChannels)
        self.outputsFrame.doubleSpinBox_ch1OutFreq.valueChanged.connect(self.updateOutputChannels)
        self.outputsFrame.doubleSpinBox_ch2OutFreq.valueChanged.connect(self.updateOutputChannels)
        self.outputsFrame.doubleSpinBox_ch1OutOffset.valueChanged.connect(self.updateOutputChannels)
        self.outputsFrame.doubleSpinBox_ch2OutOffset.valueChanged.connect(self.updateOutputChannels)
        self.outputsFrame.checkBox_ch1OuputState.stateChanged.connect(self.updateOutputChannels)
        self.outputsFrame.checkBox_ch2OuputState.stateChanged.connect(self.updateOutputChannels)

        # HMP4040
        self.outputsFrame.doubleSpinBox_outIHalogen.valueChanged.connect(self.updateHMP4040Current)
        self.outputsFrame.doubleSpinBox_outVHalogen.valueChanged.connect(self.updateHMP4040Voltage)
        self.outputsFrame.checkBox_halogenOuputState.stateChanged.connect(self.updateHMP4040State)


    def updateHMP4040Current(self):
        self.HMP4040.setCurrent(self.outputsFrame.doubleSpinBox_outIHalogen.value())
        self.outputsFrame.doubleSpinBox_outVHalogen.setValue(float(self.HMP4040.getVoltage()))
    def updateHMP4040Voltage(self):
        self.HMP4040.setVoltage(self.outputsFrame.doubleSpinBox_outVHalogen.value())
        self.outputsFrame.doubleSpinBox_outIHalogen.setValue(float(self.HMP4040.getCurrent()))
    def updateHMP4040State(self): self.HMP4040.outputState(self.outputsFrame.checkBox_halogenOuputState.checkState())



    def updateVelocityWavelength(self):
        v = self.doubleSpinBox_velocityWavelength.value()
        self.velocity.write('WAVE {:.2f}'.format(v))
        res = self.velocity.ask('WAVE?')
        if res == 'Unknown Command':
            self.print_to_dialogue('Could not change Velocity wavelength', color = 'red')
            self.doubleSpinBox_velocityWavelength.setValue(self.velocityWavelength)
        else:
            self.velocityWavelength = v

    def updatePID(self):
        P, I, D = float(self.outputsFrame.doubleSpinBox_P.value()), float(self.outputsFrame.doubleSpinBox_I.value()), float(self.outputsFrame.doubleSpinBox_D.value())
        if self.pid: self.pid.tunings = (P, I, D)

    def toggleLock(self):
        self.lockOn = not self.lockOn
        self.outputsFrame.checkBox_ch1OuputState.setCheckState(self.lockOn)
        self.outputOffset = self.outputsFrame.doubleSpinBox_outIHalogen.value()
        # Set PID limits and values
        P, I, D = float(self.outputsFrame.doubleSpinBox_P.value())/10, float(self.outputsFrame.doubleSpinBox_I.value())/10, float(self.outputsFrame.doubleSpinBox_D.value()/10)
        self.pid = PID(P, I, D, setpoint=0, output_limits=(_LASER_CURRENT_MIN - self.outputOffset, _LASER_CURRENT_MAX - self.outputOffset),
                       sample_time=0.5) if self.lockOn else None # sample_time [seconds], time at which PID is updated


    def updateOutputChannels(self):
        # TODO: add hold-update to rp
        self.changedOutputs = True
        self.rp.set_outputFunction(output=1, function=str(self.outputsFrame.comboBox_ch1OutFunction.currentText()))
        self.rp.set_outputFunction(output=2, function=str(self.outputsFrame.comboBox_ch2OutFunction.currentText()))
        self.rp.set_outputAmplitude(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutAmp.value()))
        self.rp.set_outputAmplitude(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutAmp.value()))
        self.rp.set_outputFrequency(output=1, freq=float(self.outputsFrame.doubleSpinBox_ch1OutFreq.value()))
        self.rp.set_outputFrequency(output=2, freq=float(self.outputsFrame.doubleSpinBox_ch2OutFreq.value()))
        self.rp.set_outputOffset(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutOffset.value()))
        self.rp.set_outputOffset(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutOffset.value()))
        self.rp.set_outputState(output=1, state=bool(self.outputsFrame.checkBox_ch1OuputState.checkState()))
        self.rp.set_outputState(output=2, state=bool(self.outputsFrame.checkBox_ch2OuputState.checkState()))
        self.rp.updateParameters()

    def scopeListenForMouseClick(self):
        def mouseClickOnScope(event): # what should do on mouse click, when listening
            # Find nearest peak
            if self.selectedPeaksXY is None : # id first click, create list of peaks...
                self.selectedPeaksXY = [np.array([event.xdata,event.ydata])]
                self.print_to_dialogue('Select second peak on scope...', color='green')
            else: #if second peak, append it.
                self.selectedPeaksXY.append(np.array([event.xdata,event.ydata]))
            if len(self.selectedPeaksXY) >= 2:
                # If clicked on canvas, and already has two peaks selected, stop listening for click
                self.widgetPlot.canvas.mpl_disconnect(self.listenForMouseClickCID)
                self.listenForMouseClickCID = None

        if self.listenForMouseClickCID is None:  # start listening
            self.listenForMouseClickCID = self.widgetPlot.canvas.mpl_connect('button_press_event', mouseClickOnScope)
            self.selectedPeaksXY = None
            self.print_to_dialogue('Select first peak on scope...', color = 'green')
        else: # stop listen
            self.widgetPlot.canvas.mpl_disconnect(self.listenForMouseClickCID)
            self.listenForMouseClickCID = None

    def updateSelectedPeak(self, peaksLocation):
        # Run over all current selected peaks; Assume the 1st selected peak belongs to 1st channel etc.
        # Find the closest peak to the selected one in the relevant channel; update.
        for i, curSelectedPeak in enumerate(self.selectedPeaksXY):
            if len(peaksLocation[i]) > 0:
                nearestPeakIndex = spatial.KDTree(peaksLocation[i]).query(curSelectedPeak)[1]  # [0] would have given us distance
                nearestPeakLocation = peaksLocation[i][nearestPeakIndex]
                self.selectedPeaksXY[i] = np.array(nearestPeakLocation)  # update location of selected peak to BE the nearest peak

    # Never call this method. this is called by RedPitaya
    def update_scope(self, data, parameters):
        if self.rp.firstRun:
            # Set default from display...
            self.comboBox_triggerSource.setCurrentIndex(2) # Select EXT trigger...
            self.updatePlotDisplay()
            self.setInverseChns()
            self.showHideParametersWindow()
            self.chns_update()
            self.updateOutputChannels()
            self.rp.firstRun = False

        # ---------------- Handle Redraws and data reading ----------------
        # This is true only when some parameters were changed on RP, prompting a total redraw of the plot (in other cases, updating the data suffices)
        redraw = (parameters['new_parameters'] or self.CHsUpdated) and not self.changedOutputs  # if last change was to outputs, dont bother to redraw all
        if redraw:
            self.scope_parameters = parameters  # keep all the parameters. we need them.
            self.CHsUpdated = False
        self.Rb_lines_Data[self.Avg_indx % self.Avg_num[0]] = data[0]  # Insert new data
        self.Cavity_Transmission_Data[self.Avg_indx % self.Avg_num[1]] = data[1]  # Insert new data
        self.Avg_indx = self.Avg_indx + 1
        self.changedOutputs = False

        # ---------------- Average data  ----------------
        # Calculate avarage data and find peaks position (indx) and properties:
        Avg_data = []
        if self.checkBox_Rb_lines.isChecked():
            # TODO: Tal put a sqrt on the avg here - why?
            self.Rb_lines_Avg_Data = np.average(self.Rb_lines_Data, axis=0)
            Avg_data = Avg_data + [self.Rb_lines_Avg_Data]
        if self.checkBox_Cavity_transm.isChecked():
            self.Cavity_Transmission_Avg_Data = np.average(self.Cavity_Transmission_Data, axis=0)
            Avg_data = Avg_data + [self.Cavity_Transmission_Avg_Data]

        # ---------------- Handle Rb Peaks ----------------
        Rb_peaks, Cavity_peak, Rb_properties, Cavity_properties = [], [], {}, {} # by default, none
        if self.checkBox_Rb_lines.isChecked():
            Rb_peaks, Rb_properties = find_peaks(self.Rb_lines_Avg_Data,
                                                 distance=float(self.spinBox_distance_ch1.value()),
                                                 prominence=float(self.doubleSpinBox_prominence_ch1.value()),
                                                 width=float(self.spinBox_width_ch1.value()))
        if self.checkBox_Cavity_transm.isChecked():
            Cavity_peak, Cavity_properties = find_peaks(self.Cavity_Transmission_Avg_Data,
                                                        distance=float(self.spinBox_distance_ch2.value()),
                                                        prominence=float(self.doubleSpinBox_prominence_ch2.value()),
                                                        width=float(self.spinBox_width_ch2.value()))

        # ------- Scales -------
        # At this point we assume we have a corrcet calibration polynomial in @self.index_to_freq
        # Set Values for x-axis frequency:
        time_scale = float(self.scope_parameters['OSC_TIME_SCALE']['value'])
        indx_to_time = float(10 * time_scale / self.scope_parameters['OSC_DATA_SIZE']['value'])
        # time-scale
        x_axis = np.linspace(0, time_scale * 10, num=int(self.scope_parameters['OSC_DATA_SIZE']['value']))
        x_ticks = np.arange(x_axis[0], x_axis[-1], time_scale)

        # Secondary axis
        indx_to_freq = self.indx_to_freq[0]
        def timeToFreqScale(t):
            print(indx_to_freq)
            return (t - Rb_peaks[0]) * indx_to_freq
        def freqToTimeScale(f):
            print(indx_to_freq)
            return f / indx_to_freq + Rb_peaks[0]

        # ----------- Y scaling and offset -----------
        y_scale = [float(self.doubleSpinBox_VtoDiv_ch1.text()), float(self.doubleSpinBox_VtoDiv_ch2.text())]
        y_offset = [float(self.doubleSpinBox_VOffset_ch1.text()), float(self.doubleSpinBox_VOffset_ch2.text())]
        # Create two array of ticks, for the two scales of the two channels
        y_ticks = [np.arange(y_offset[i] - y_scale[i] * 5, y_offset[i] + y_scale[i] * 5, y_scale[i])
                   for i in range(len(y_scale))]
        # --------- select peak -----------
        # At this point we have the location of the selected peak, either by (1) recent mouse click or (2) the last known location of the peak
        if self.selectedPeaksXY is not None and type(self.selectedPeaksXY) == list:# and len(self.selectedPeaksXY) == 2 and type(self.selectedPeaksXY[0]) == np.ndarray and type(self.selectedPeaksXY[1]) == np.ndarray:
            chn1_peaksLocation = np.array([[x_axis[p], Avg_data[0][p]] for p in Rb_peaks])  # all the peaks as coordinates
            chn2_peaksLocation = np.array([[x_axis[p], Avg_data[1][p]] for p in Cavity_peak])  # all the peaks as coordinates
            self.updateSelectedPeak([chn1_peaksLocation, chn2_peaksLocation])

        # ----------- text box -----------
        # to be printed in lower right corner
        text_box_string = None

        if self.outputsFrame.checkBox_fitLorentzian.isChecked():
            popt = self.fitMultipleLorentzians(xData=x_axis, yData=Avg_data[0], peaks_indices=Rb_peaks,
                                        peaks_init_width=(Rb_properties['widths'] * indx_to_time))  # just an attempt. this runs very slowly.
            params_text = self.multipleLorentziansParamsToText(popt)
            text_box_string = 'Calibration: \n' + str(self.indx_to_freq) +'\n'
            text_box_string += 'Found %d Lorentzians: \n'%len(Rb_peaks) + params_text

        # --------- plot ---------
        # Prepare data for display:
        labels = ["CH1 - Vortex Rb lines", "CH2 - Cavity transmission"]
        self.widgetPlot.plot_Scope(x_axis, Avg_data, autoscale=self.checkBox_plotAutoscale.isChecked(), redraw=redraw, labels = labels, x_ticks = x_ticks, y_ticks= y_ticks,
                                   aux_plotting_func = self.widgetPlot.plot_Scatter, scatter_y_data = np.concatenate([Avg_data[0][Rb_peaks], Avg_data[1][Cavity_peak]]),
                                   scatter_x_data = np.concatenate([x_axis[Rb_peaks], x_axis[Cavity_peak]]),mark_peak = self.selectedPeaksXY, text_box = text_box_string)

        # --------- Lock -----------
        if self.lockOn and self.selectedPeaksXY and len(self.selectedPeaksXY) == 2: # if, and only if, we have selected two peaks to lock on
           self.lockPeakToPeak()

        # -------- Save Data  --------:
        if self.checkBox_saveData.isChecked():
            self.saveCurrentDataClicked()

    def lockPeakToPeak(self):
        errorDirection = 1 if self.outputsFrame.checkBox_lockInverse.isChecked() else - 1
        errorSignal = 1e-1 * (self.selectedPeaksXY[1][0] - self.selectedPeaksXY[0][0] + float(self.outputsFrame.doubleSpinBox_lockOffset.value())) * (errorDirection)
        # Error signal times 1e-3 makes sense -> mili-amps. also good for de-facto units
        output = self.pid(errorSignal)
        output = float(self.outputOffset + output)
        if self.debugging: print('Error Signal: ', errorSignal, 'Output: ', output)
        # ------- set output --------------
        # It's a problem with Red-Pitaya: to get 10V DC output, one has to set both Amp and Offset to 5V
        if self.outputsFrame.checkBox_halogenOuputState.isChecked():
            # Lock using halogen
            #if output > _HALOGEN_VOLTAGE_LIMIT: output = _HALOGEN_VOLTAGE_LIMIT
            if output > _LASER_CURRENT_MAX: output = _LASER_CURRENT_MAX
            if output < _LASER_CURRENT_MIN: output = _LASER_CURRENT_MIN
            if output != self.outputsFrame.doubleSpinBox_outIHalogen.value(): # if output is different, only then send update command
                self.outputsFrame.doubleSpinBox_outIHalogen.setValue(output)
        else: # lock with RedPitaya
            self.outputsFrame.doubleSpinBox_ch1OutAmp.setValue(float(output) / 2)
            self.outputsFrame.doubleSpinBox_ch1OutOffset.setValue(float(output) / 2)


if __name__ == "__main__":
    app = QApplication([])
    simulation = False if os.getlogin() == 'orelb' else True
    window = Cavity_lock_GUI(simulation=simulation, debugging = True)
    window.show()
    app.exec_()
    sys.exit(app.exec_())