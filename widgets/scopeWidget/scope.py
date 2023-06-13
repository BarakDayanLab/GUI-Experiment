
from PyQt5 import uic
import time
from functions import RedPitayaWebsocket
from scipy import optimize,spatial
from scipy.signal import find_peaks
# import vxi11 # https://github.com/python-ivi/python-vxi11
import os
import sys
import numpy as np
from PyQt5.QtWidgets import QApplication
import matplotlib
from PyQt5.QtCore import QThreadPool
from datetime import date, datetime
from widgets.worker import Worker
import matplotlib.pyplot as plt
from functions.stirap.calculate_Nat_stirap import NAtoms
_CONNECTION_ATTMPTS = 2

try:
    from functions.cavity_lock.cavity_lock import CavityLock
except:
    print("Run without calculate OD")
if matplotlib.get_backend() != 'Qt5Agg':
    matplotlib.use('Qt5Agg')

from widgets.quantumWidget import QuantumWidget


class Scope_GUI(QuantumWidget):
    SCALE_OPTIONS = ['ms', 'us', 'ns']

    def __init__(self, Parent=None, ui=None, simulation=True, RedPitayaHost=None, debugging=False):
        if Parent is not None:
            self.Parent = Parent
        ui = os.path.join(os.path.dirname(__file__), "scopeWidgetGUI.ui") if ui is None else ui
        self.host = RedPitayaHost
        self.debugging = debugging
        super().__init__(ui, simulation)
        # up to here, nothing to change.

        if __name__ == "__main__":
            self.threadpool = QThreadPool()
            print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.connection_attempt = 0  # This holds connection attmeps. As long as this is < than _CONNECTION_ATTMPTS, will try to reconnect
        self.scope_parameters = {'new_parameters': False, 'OSC_TIME_SCALE': {'value':'1'}, 'OSC_CH1_SCALE': {'value':'1'},'OSC_CH1_SCALE': {'value':'1'}, 'OSC_DATA_SIZE':{'value':1024}}
        self.CHsUpdated = False
        self.rp = None  # Place holder
        self.isSavingNDataFiles = False
        self.signalLength = self.scope_parameters['OSC_DATA_SIZE']['value']  # 1024 by default
        self.indx_to_freq = [0]
        self.time_scale_units = 1  # 0=ms, 1=us, 2=ns

        # -- connect --
        self.connectButtonsAndSpinboxes()
        self.updateAveraging()
        #self.update_plot_params()

        self.utils_connect_worker()


    def connectButtonsAndSpinboxes(self):
        self.pushButton_utils_Connect.clicked.connect(self.utils_connect_worker)
        self.pushButton_saveCurrentData.clicked.connect(self.saveCurrentDataClicked)
        self.pushButton_updatePlotDisplay.clicked.connect(self.updatePlotDisplay)
        self.checkBox_iPython.clicked.connect(self.showHideConsole)
        self.checkBox_parameters.clicked.connect(self.showHideParametersWindow)
        self.checkBox_CH1Inverse.clicked.connect(self.setInverseChns)
        self.checkBox_CH2Inverse.clicked.connect(self.setInverseChns)
        self.label_timeDiv.mousePressEvent = self.setTimeDiv

        self.connect_custom_ui_controls()

    # Switch the scales from millis -> micros -> nanos
    def setTimeDiv(self, event):
        if event.type() != 2:
            return  # Not mouse click

        self.time_scale_units = (self.time_scale_units + 1) % len(self.SCALE_OPTIONS)

        # Set the label
        self.label_timeDiv.setText("Time/Div [%s]" % self.SCALE_OPTIONS[self.time_scale_units])

        self.updateTimeScale(True)

    def setInverseChns(self):
        self.rp.set_inverseChannel(ch=1, value = self.checkBox_CH1Inverse.isChecked())
        self.rp.set_inverseChannel(ch=2, value =  self.checkBox_CH2Inverse.isChecked())

    def update_plot_params(self):
        raise NotImplementedError
        # TODO: remove the code below - this method is the same as updateAveraging
        # self.Avg_num = [int(self.spinBox_averaging_ch1.value()), int(self.spinBox_averaging_ch2.value())]
        # self.Rb_lines_Data = np.zeros((self.Avg_num[0], self.signalLength))  # Place holder
        # self.Cavity_Transmission_Data = np.zeros((self.Avg_num[1], self.signalLength))  # Place holder
        # self.Avg_indx = 0

    def updateChannelCoupling(self):
        ch1_coupling = self.comboBox_channel1Coupling.currentText()  # text
        self.rp.set_inputAcDcCoupling(channel=1, coupling=ch1_coupling.replace(' Coupling', ''), verbose=True)
        ch2_coupling = self.comboBox_channel2Coupling.currentText()  # text
        self.rp.set_inputAcDcCoupling(channel=2, coupling=ch2_coupling.replace(' Coupling', ''), verbose=True)

    def updateTriggerSource(self):
        trigger_source = self.comboBox_triggerSource.currentText()  # text
        self.rp.set_triggerSource(trigger_source, True)

    def updateTriggerSweep(self):
        trigger_sweep = self.comboBox_triggerSweep.currentText()  # get sweep policy (SINGLE, AUTO, NORMAL
        self.rp.set_triggerSweep(trigger_sweep.replace('Trg:', '').upper(), True)

    def updateTriggerSlope(self):
        trigger_slope = self.comboBox_triggerSlope.currentText()  # get trigger slope (RISING, FALLING)
        self.rp.set_triggerSlope(trigger_slope.replace('Trg:', '').upper(), True)

    # TODO: Separate this to 2 functions
    # Update the Red Pitaya with trigger settings as appears in UI
    def updateTriggerDelay(self):
        trigger_time = float(self.doubleSpinBox_triggerDelay.value())  # ms
        trigger_level = float(self.doubleSpinBox_triggerLevel.value())  # in V
        self.rp.set_triggerDelay(trigger_time, True)
        self.rp.set_triggerLevel(trigger_level*1000, True)
        # self.print_to_dialogue("Trigger delay changed to %f ms; Source: %s; Level: %2.f [V]" % (t,s,l))

    # Update the RedPitaya with the timescale as appears in UI
    def updateTimeScale(self, verbose=False):
        t = float(self.doubleSpinBox_timeScale.text())
        factor = pow(10,self.time_scale_units*3)
        t = t / factor  # us - like dividing by 10^3
        self.rp.set_timeScale(t)
        #if verbose: self.print_to_dialogue("Time scale changed to %f %s" % (t, self.SCALE_OPTION[self.time_scale_units]))

    # Update the average sampling for the two channels
    # (update the locker subclass, so it can zero its data buffers)
    def updateAveraging(self):
        self.Avg_num = [int(self.spinBox_averaging_ch1.value()), int(self.spinBox_averaging_ch2.value())]
        # self.Rb_lines_Data = np.zeros((self.Avg_num[0], self.signalLength))  # Place holder
        # self.Cavity_Transmission_Data = np.zeros((self.Avg_num[1], self.signalLength))  # Place holder
        self.Avg_indx = 0
        # self.print_to_dialogue("Data averaging changed to %i" % self.Avg_num)
        # Update the locker subclass that the params changed
        self.averaging_parameters_updated()

    # This is called on first-run or when "update" is clicked in UX
    # It will update the RedPitaya with the settings in UI
    def updatePlotDisplay(self):
        self.updateTriggerDelay()
        self.updateTriggerSweep()
        self.updateTriggerSource()
        self.updateTriggerSlope()
        self.updateTimeScale()
        self.updateAveraging()
        self.CHsUpdated = True

    def chns_update(self):
        self.scope_parameters['new_parameters'] = True

    def enable_interface(self, v): #TODO ?????
        self.frame_4.setEnabled(v)
        self.frame_parameters.setEnabled(v)

    def utils_connect_worker(self):
        worker = Worker(self.utils_connect)
        self.pushButton_utils_Connect.setDisabled(True)
        worker.signals.finished.connect(self.utils_connect_finished)
        self.threadpool.start(worker)

    def utils_connect_finished(self):
        self.enable_interface(True)
        self.pushButton_utils_Connect.setEnabled(True)

    def utils_connect(self, progress_callback):
        self.print_to_dialogue("Connecting to RedPitayas...")
        time.sleep(0.1)
        # self.connectOPX()
        # ---- Connect Red-Pitaya ------
        RPworker = Worker(self.redPitayaConnect)  # Trying to work on a different thread...
        self.threadpool.start(RPworker)

    def saveCurrentDataClicked(self):
        self.isSavingNDataFiles = True

    def saveCurrentData(self, extra_text = ''):
        extra_text = str(extra_text)
        if self.isSavingNDataFiles: # if we are saving N files
            if self.spinBox_saveNFiles.value() > 1:
                self.spinBox_saveNFiles.setValue(self.spinBox_saveNFiles.value() - 1)  # decrease files to save by 1
            elif self.spinBox_saveNFiles.value() == 1:
                self.isSavingNDataFiles = False

        timeScale = np.linspace(0, float(self.scope_parameters['OSC_TIME_SCALE']['value']) * 10, num=int(self.scope_parameters['OSC_DATA_SIZE']['value']))
        now = datetime.now()
        today = date.today()
        # datadir = os.path.join("C:\\", "Pycharm", "Expriements", "DATA", "CavityLock")
        datadir = os.path.join("U:\\", "Lab_2021-2022", "Experiment_results", "Python Data")
        todayformated = today.strftime("%B-%d-%Y")
        todaydatadir = os.path.join(datadir, todayformated)
        nowformated = now.strftime("%H-%M-%S_%f")
        try:
            os.makedirs(todaydatadir)
            if not self.checkBox_saveData.isChecked():
                self.print_to_dialogue("Created folder Lab_2021-2022/Experiment_results/Python Data/%s" % (todayformated))
                self.print_to_dialogue("Data Saved")
        except FileExistsError:
            if not self.checkBox_saveData.isChecked():
                self.print_to_dialogue("Data Saved")

        self.datafile = os.path.join(todaydatadir, nowformated + ".txt")
        meta = "Traces from the RedPitaya, obtained on %s at %s.\n" % (todayformated, nowformated)
        cmnt = self.lineEdit_fileComment.text()
        # np.savez_compressed(os.path.join(todaydatadir, nowformated), CH1=self.Rb_lines_Avg_Data, CH2=self.Cavity_Transmission_Data, time=timeScale, meta=meta)
        np.savez_compressed(os.path.join(todaydatadir, nowformated), CH1=self.Rb_lines_Avg_Data,CH2=self.Cavity_Transmission_Avg_Data, time=timeScale, meta=meta, comment = cmnt, extra_text = extra_text)

    def redPitayaConnect(self, progress_callback):
        RpHost = ["rp-ffffb4.local","rp-f08c22.local", "rp-f08c36.local"]
        if self.host == None:
            self.rp = RedPitayaWebsocket.Redpitaya(host="rp-ffffb4.local",
                                                   got_data_callback=self.update_scope,
                                                   dialogue_print_callback=self.print_to_dialogue,
                                                   debugging= self.debugging)
        else:
            self.rp = RedPitayaWebsocket.Redpitaya(host=self.host,
                                                   got_data_callback=self.update_scope,
                                                   dialogue_print_callback=self.print_to_dialogue,
                                                   debugging= self.debugging)

        if self.rp.connected:
            self.connection_attempt = 0 # connection
            self.print_to_dialogue("RedPitayas are connected.", color='green')
            self.rp.run()
        else:
            self.print_to_dialogue("Unable to connect to RedPitaya.", color='red')
            self.rp.close()
            self.rp = None
            if self.connection_attempt < _CONNECTION_ATTMPTS:
                self.print_to_dialogue('Trying to reconnect... (attempt = %d out of %d)' % (self.connection_attempt + 1, _CONNECTION_ATTMPTS))
                self.connection_attempt = self.connection_attempt + 1
                self.redPitayaConnect(progress_callback)



    # Never call this method. this is called by RedPitaya and implemented by sub-classes
    def update_scope(self, data, parameters):
        raise NotImplementedError

        # TODO: after we ensure this class is not called by anyone, we can remove all the code below

        if self.rp.firstRun:
            # Set default from display...
            self.comboBox_triggerSource.setCurrentIndex(2)  # Select EXT trigger...
            self.updatePlotDisplay()
            self.setInverseChns()
            self.showHideParametersWindow()
            self.chns_update()
            self.rp.firstRun = False

        # ---------------- Handle duplicate data ----------------
        # It seems Red Pitaya tends to send the same data more than once. That is, although it has not been triggered,
        # scope will send current data as fast as it can.
        # Following lines aim to prevent unnecessary work
        previousDataIndex = self.Avg_indx - 1
        if np.array_equal(self.Rb_lines_Data[previousDataIndex % self.Avg_num[0]], data[0]) or np.array_equal(
                self.Cavity_Transmission_Data[previousDataIndex % self.Avg_num[1]], data[1]):
            return
        # ---------------- Handle Redraws and data reading ----------------
        # This is true only when some parameters were changed on RP, prompting a total redraw of the plot (in other cases, updating the data suffices)
        redraw = (parameters['new_parameters'] or self.CHsUpdated)
        if redraw:
            self.scope_parameters.update(parameters)  # keep all the parameters. we need them.
            self.CHsUpdated = False
        self.Rb_lines_Data[self.Avg_indx % self.Avg_num[0]] = data[0]  # Insert new data
        self.Cavity_Transmission_Data[self.Avg_indx % self.Avg_num[1]] = data[1]  # Insert new data
        self.Avg_indx = self.Avg_indx + 1
        # ---------------- Average data  ----------------
        # Calculate average data and find peaks position (indx) and properties:
        Avg_data = []
        if self.checkBox_Rb_lines.isChecked():
            self.Rb_lines_Avg_Data = np.average(self.Rb_lines_Data, axis=0)
            Avg_data = Avg_data + [self.Rb_lines_Avg_Data]
        if self.checkBox_Cavity_transm.isChecked():
            self.Cavity_Transmission_Avg_Data = np.average(self.Cavity_Transmission_Data, axis=0)
            Avg_data = Avg_data + [self.Cavity_Transmission_Avg_Data]

        # ---------------- Handle Rb Peaks ----------------
        Rb_peaks,Cavity_peak, Rb_properties, Cavity_properties = [], [],{},{} # by default, none
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

        # ----------- Secondary X axis -----------
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

        # ----------- text box -----------
        # to be printed in lower right corner
        text_box_string = None

        # --------- plot ---------
        # Prepare data for display:
        labels = ["CH1 - Vortex Rb lines", "CH2 - Cavity transmission"]
        self.widgetPlot.plot_Scope(x_axis, Avg_data, autoscale=self.checkBox_plotAutoscale.isChecked(), redraw=redraw, labels = labels, x_ticks = x_ticks, y_ticks= y_ticks,
                                   aux_plotting_func = self.widgetPlot.plot_Scatter, scatter_y_data = np.concatenate([Avg_data[0][Rb_peaks], Avg_data[1][Cavity_peak]]),
                                   scatter_x_data = np.concatenate([x_axis[Rb_peaks], x_axis[Cavity_peak]]),text_box = text_box_string)

        # -------- Save Data  --------:
        if self.checkBox_saveData.isChecked() or self.isSavingNDataFiles:
            self.saveCurrentData()


    def printPeaksInformation(self):
        print('printPeaksInformation', str(self.indx_to_freq))

    def lorentzian(self,k_ex, k_tot, h, f_offset, offset, amp, f):
        '''
        k_ex,k_tot,h,f,f_offset - Hz
        amp,offset - [V]
        '''
        delta = f - f_offset
        z = offset + amp * np.power(np.abs(2 * k_ex * h / (1j * delta + k_tot) ** 2 + h ** 2), 2)
        return z

    def fitMultipleLorentzians(self, xData, yData,params_0):
        # -- fit functions ---
        # def multi_lorentz_curve_fit(x, *params):
        #     shift = params[0]  # Scalar shift
        #     paramsRest = params[1:]  # These are the atcual parameters.
        #     assert not (len(paramsRest) % 3)  # makes sure we have enough params
        #     return shift + sum([lorentzian(x, *paramsRest[i: i + 3]) for i in range(0, len(paramsRest), 3)])

        # -------- Begin fit: --------------
        # pub = [0.5, 1.5]  # peak_uncertain_bounds
        startValues = []
        # for k, i in enumerate(peaks_indices):
        #     startValues += params_0
        # lower_bounds = [-20] + [v * pub[0] for v in startValues]
        # upper_bounds = [20] + [v * pub[1] for v in startValues]
        # bounds = [lower_bounds, upper_bounds]
        # startValues = [min(yData)] + startValues  # This is the constant from which we start the Lorentzian fits - ideally, 0
        popt, pcov = optimize.curve_fit(self.lorentzian, xData, yData, p0=params_0, maxfev=50000)
        #ys = [multi_lorentz_curve_fit(x, popt) for x in xData]
        return (popt)

    def multipleLorentziansParamsToText(self, popt):
        text = ''
        params = popt
        text += 'f_0' +' = %.2f; \n' % params[3]
        text += 'k_i = %.2f; \n' % (params[1]-params[0])
        text += 'k_total = %.2f; \n' % params[1]
        text += 'h' + ' = %.2f \n' %  params[2]
        return (text)



if __name__ == "__main__":
    app = QApplication([])
    simulation = False if os.getlogin() == 'orelb' else True
    window = Scope_GUI(simulation=simulation)
    window.show()
    app.exec_()
    sys.exit(app.exec_())