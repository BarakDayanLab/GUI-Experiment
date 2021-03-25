# -*- coding: utf-8 -*-
"""
Created on Sun Jan 10 12:17:08 2021

@author: Jeremy Raskop
"""

from functions.od import scpi
from scipy import optimize
import os
import sys
import numpy as np
from PyQt5.QtWidgets import QApplication
import matplotlib
from PyQt5.QtCore import QThreadPool
from datetime import date, datetime
from widgets.worker import Worker
try:
    from calculate_OD import OD_exp
except:
    print("Run without calculate OD")
if matplotlib.get_backend()!='Qt5Agg':
    matplotlib.use('Qt5Agg')

from widgets.quantumWidget import QuantumWidget


class STIRAP_gui (QuantumWidget):
    def __init__(self, Parent=None, ui=None, simulation=True):
        if Parent is not None:
            self.Parent = Parent
        ui = os.path.join(os.path.dirname(__file__), "gui.ui") if ui is None else ui
        super().__init__(ui, simulation)
        if __name__ == "__main__":
            self.threadpool = QThreadPool()
            print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        self.widgetPlot.plot([None], [None])
        self.checkBox_iPython.clicked.connect(self.showHideConsole)
        self.checkBox_parameters.clicked.connect(self.showHideParametersWindow)
        
        # self.checkBox_OD.clicked.connect(self.acquire_OD_worker)
        # self.checkBox_Repump.clicked.connect(self.acquire_Nat_worker)
        self.pushButton_utils_Connect.clicked.connect(self.utils_connect_worker)
        self.pushButton_update.clicked.connect(self.change_probe_frequency)
        self.pushButton_Cursor.clicked.connect(self.positionNatCursors)
        # self.pushButton_CursorsOD.clicked.connect(self.positionNatODCursors)
        self.pushButton_saveCurrentData.clicked.connect(self.saveCurrentDataClicked)
        self.enable_interface(False)

        # self.decimation = 8
        self.cursorsOD = list(np.array([145, 312, 535, 705]))
        self.cursorsNat = list(np.array([145, 312, 535, 705]))

        # self.rplastdataNat1, self.rplastdataNat2 = [], []
        # self.rplastdataOD1, self.rplastdataOD2 = [], []
        # self.rplastdata1, self.rplastdata2 = [], []
        
        self.last_data1_OD, self.last_data2_OD = [], []
        self.last_data1_Sigma, self.last_data2_Sigma = [], []
        self.last_data1_Pi, self.last_data2_Pi = [], []
        self.rptimes = []
        self.datafile = None
        self.display_traces_worker()

    def saveCurrentDataClicked(self):
        now = datetime.now()
        today = date.today()
        datadir = os.path.join("C:\\", "Pycharm", "Expriements", "DATA", "STIRAP")
        todayformated = today.strftime("%B-%d-%Y")
        todaydatadir = os.path.join(datadir, todayformated)
        nowformated = now.strftime("%Hh%Mm%Ss")
        try:
            os.makedirs(todaydatadir)
            self.print_to_dialogue("Created folder DATA/STIRAP/%s" % (todayformated))
            self.print_to_dialogue("Data Saved")
        except FileExistsError:
            self.print_to_dialogue("Data Saved")

        self.datafile = os.path.join(todaydatadir, nowformated + ".txt")
        meta = "Traces from the RedPitaya, obtained on %s at %s.\n" % (todayformated, nowformated)

        # np.savetxt(self.datafile, np.transpose([self.rplastdata1, self.rplastdata2]),  fmt='%.6e', header=header)
        np.savez_compressed(os.path.join(todaydatadir, nowformated), 
                            CH1_OD=self.last_data1_OD, 
                            CH2_Depump=self.last_data2_OD,
                            CH1_Sigma = self.last_data1_Sigma,
                            CH2_Sigma = self.last_data2_Sigma,
                            CH1_Pi = self.last_data1_Pi,
                            CH2_Pi = self.last_data2_Pi,
                            times=self.rptimes, 
                            meta=meta
                            )

    def positionNatCursors(self):
        self.alert_box("Turn of the B-field gradient and make sure that the depumper pulses are properly contained within the plot.")
        nat = np.array(self.rplastdataNat1)
        dy = nat.max() - nat.min()
        tresholdlevel = nat.min()+dy/2
        a, b, d = 0, 0, 0
        for i, el in enumerate(nat):
            if el>=tresholdlevel:
                a = int(i-15)
                break
        for i, el in enumerate(nat[a+100:]):
            if el<=tresholdlevel:
                d = int(i)
                break
        for i, el in enumerate(nat[a+d+400:]):
            if el>=tresholdlevel:
                b = int(i+a+d+400 - 15)
                break
        res = optimize.minimize(self.odexp.tominimizeNat, np.array([b]), args=(a, d, nat))
        print(res)
        b_opt = res.x[0]
        self.cursorsNat = np.array([a, a + d, b_opt, b_opt + d])/self.rp_OD.sampling_rate*1e6
        print([a, a + d, b_opt, b_opt + d])
        self.print_to_dialogue("Minimized down to Nat = %.0f * 1e3"%(res.fun/1e3))

    def positionNatODCursors(self):
        self.alert_box("Turn of the B-field gradient and make sure that the OD pulses are properly contained within the plot.")
        od = np.array(self.rplastdataOD2)
        dy = od.max() - od.min()
        tresholdlevel = od.min()+dy/2
        a, b, d = 0, 0, 0
        for i, el in enumerate(od):
            if el>=tresholdlevel:
                a = int(i-15)
                break
        for i, el in enumerate(od[a+100:]):
            if el<=tresholdlevel:
                d = int(i)
                break
        for i, el in enumerate(od[a+d+400:]):
            if el>=tresholdlevel:
                b = int(i+a+d+400 - 15)
                break
        res = optimize.minimize(self.odexp.tominimizeNat, np.array([b]), args=(a, d, od))
        print(res)
        b_opt = res.x[0]
        if res.success:
            self.cursorsOD = np.array([a, a + d, b_opt, b_opt + d])/self.rp_OD.sampling_rate*1e6
            print([a, a + d, b_opt, b_opt + d])
            self.print_to_dialogue("Minimized down to Nat = %.0f * 1e3"%(res.fun/1e3))
        else:
            self.print_to_dialogue("Failed to find optimal position for cursors")

    def enable_interface(self, v):
        self.checkBox_OD.setEnabled(v)
        self.checkBox_Repump.setEnabled(v)
        self.frame_4.setEnabled(v)
        # self.checkBox_parameters.setEnabled(v)
        self.frame_parameters.setEnabled(v)

    def change_probe_frequency(self):
        detuning = self.doubleSpinBox_frequency.value()
        self.OPX.qm.set_intermediate_frequency("AOM_2-3'",(93 + detuning)*1e6)
        self.print_to_dialogue("Detuning set to %.1f MHz"%(detuning))

    def get_OD_worker(self):
        worker = Worker(self.get_OD)
        self.print_to_dialogue("Acquiring OD...")
        worker.signals.finished.connect(self.get_OD_done)
        self.threadpool.start(worker)

    def get_OD_done(self):
        self.print_to_dialogue("OD acquired")

    def get_OD(self, progress_callback, singleshot=True):
        if singleshot:
            odtime = self.doubleSpinBox_ODtimes.value()
            self.OPX.MeasureOD(odtime)
        # data = self.rp.get_trace(channel=2)
        data1, data2 = self.rp_OD.get_traces()
        self.rplastdataOD1, self.rplastdataOD2 = data1, data2
        self.rplastdata1, self.rplastdata2 = data1, data2
        times = np.arange(0, len(data1) / self.rp_OD.sampling_rate, 1. / self.rp_OD.sampling_rate) * 1e6
        self.rptimes = times
        beamRadius = 200e-6
        wavelength = 780e-9
        self.odexp = OD_exp()
        OD = self.odexp.calculate_OD(beamRadius, times, self.cursorsOD, data2, wavelength)
        self.widgetPlot.plot_OD(times, data1, data2, self.cursorsOD, autoscale=self.checkBox_plotAutoscale.isChecked())
        self.print_to_dialogue("OD = %.2f"%(OD))
        if self.checkBox_saveData.isChecked():
            self.saveCurrentDataClicked()
        # self.OPX.update_parameters()

    def acquire_OD_worker(self):
        if self.checkBox_OD.isChecked():
            worker = Worker(self.acquire_OD)
            self.print_to_dialogue("Acquiring OD...")
            worker.signals.finished.connect(self.acquire_OD_done)
            self.threadpool.start(worker)

    def acquire_OD_done(self):
        # self.OPX.OD_switch(False)
        self.print_to_dialogue("Stopped acquiring OD")

    def acquire_OD(self, progress_callback):
        # self.OPX.OD_switch(True)
        while self.checkBox_OD.isChecked():
            self.get_OD(1, singleshot=False)

    def acquire_Nat_worker(self):
        if self.checkBox_Repump.isChecked():
            worker = Worker(self.acquire_Nat)
            self.print_to_dialogue("Acquiring Nat...")
            worker.signals.finished.connect(self.acquire_Nat_done)
            self.threadpool.start(worker)

    def acquire_Nat_done(self):
        self.print_to_dialogue("Done acquiring Nat.")

    def acquire_Nat(self,progress_callback):
        # self.OPX.OD_switch(True)
        while self.checkBox_Repump.isChecked():
            self.get_Nat(1, singleshot=False)

    def get_Nat_worker(self):
        worker = Worker(self.get_Nat)
        self.print_to_dialogue("Acquiring number of atoms...")
        # self.print_to_dialogue("Acquiring number of atoms...")
        worker.signals.finished.connect(self.get_Nat_done)
        self.threadpool.start(worker)

    def get_Nat_done(self):
        self.print_to_dialogue("Number of atoms acquired")

    def get_Nat(self, progress_callback, singleshot=True):
        if singleshot:
            self.OPX.MeasureNatoms(0)
        # data = self.rp_OD.get_trace(channel=1)
        data1, data2 = self.rp_OD.get_traces()
        self.rplastdataNat1, self.rplastdataNat2 = data1, data2
        self.rplastdata1, self.rplastdata2 = data1, data2
        times = np.arange(0, len(data1) / self.rp_OD.sampling_rate, 1. / self.rp_OD.sampling_rate) * 1e6
        self.rptimes = times

        self.odexp = OD_exp()
        Nat = self.odexp.calculate_Nat(self.cursorsNat, times, data1)
        self.widgetPlot.plot_OD(times, data1, data2, self.cursorsNat, autoscale=self.checkBox_plotAutoscale.isChecked())
        self.print_to_dialogue("Number of atoms = %.1f *1e6"%(Nat/1e6))
        if self.checkBox_saveData.isChecked():
            self.saveCurrentDataClicked()
        # self.print_to_dialogue("OD = %.2f"%(OD))

    def display_traces_worker(self):
        worker = Worker(self.display_traces)
        self.threadpool.start(worker)

    def display_traces(self):
        data1_OD, data2_OD = self.rp_OD.get_traces()
        data1_Sigma, data2_Sigma = self.rp_Sigma.get_traces()
        data1_Pi, data2_Pi = self.rp_Pi.get_traces()
        self.last_data1_OD, self.last_data2_OD = self.data1_OD, self.data2_OD
        self.last_data1_Sigma, self.last_data2_Sigma = self.data1_Sigma, self.data2_Sigma
        self.last_data1_Pi, self.last_data2_Pi = self.data1_Pi, self.data2_Pi
        times_OD = np.arange(0, len(data1_OD) / self.rp_OD.sampling_rate / self.rp_OD.decimation, 1. / self.rp_OD.sampling_rate / self.rp_OD.decimation) * 1e6
        times_Sigma = np.arange(0, len(data1_Sigma) / self.rp_Sigma.sampling_rate / self.rp_Sigma.decimation, 1. / self.rp_Sigma.sampling_rate / self.rp_Sigma.decimation) * 1e6
        times_Pi = np.arange(0, len(data1_Pi) / self.rp_Pi.sampling_rate / self.rp_Pi.decimation, 1. / self.rp_Pi.sampling_rate / self.rp_Pi.decimation) * 1e6
        self.rptimes = times_OD
        data = [data1_OD,
                data2_OD,
                data1_Sigma,
                data2_Sigma,
                data1_Sigma + data2_Sigma,
                data1_Pi,
                ]
        truthiness = [self.checkBox_OD.isChecked(), 
                      self.checkBox_Repump.isChecked(),
                      self.checkBox_CH1.isChecked(),
                      self.checkBox_CH2.isChecked(),
                      self.checkBox_CH1CH2Sum.isChecked(),
                      self.checkBox_Pi.isChecked(),
                      ]
        labels = ["OD", "Depump", "CH1", "CH2", "CH1+CH2", "Pi"]
        self.widgetPlot.plot_traces(data, truthiness, labels)
        if self.checkBox_saveData.isChecked():
            self.saveCurrentDataClicked()

    def set_decimation(self, dec):
        self.rp_OD.set_decimation(dec)
        self.rp_Sigma.set_decimation(dec)
        self.rp_Pi.set_decimation(dec)

    def set_delay(self, delay):
        self.rp_OD.set_delay(delay)
        self.rp_Sigma.set_delay(delay)
        self.rp_Pi.set_delay(delay)

    def utils_connect_worker(self):
        worker = Worker(self.utils_connect)
        self.pushButton_utils_Connect.setDisabled(True)
        worker.signals.finished.connect(self.utils_connect_finished)
        # worker.signals.progress.connect(self.progress_fn)
        self.threadpool.start(worker)

    def utils_connect_finished(self):
        self.enable_interface(True)
        self.pushButton_utils_Connect.setEnabled(True)

    def utils_connect(self, progress_callback):
        self.print_to_dialogue("Connecting to Red Pitaya...")
        
        try:
            self.rp_OD = scpi.Redpitaya("rp-f0629e.local")
            self.print_to_dialogue("Connected to Red Pitaya OD")
        except TypeError:
            self.print_to_dialogue("Couldn't connect to Red Pitaya OD")
            
        try:
            self.rp_sigma = scpi.Redpitaya("rp-f08c22.local")
            self.print_to_dialogue("Connected to Red Pitaya Sigma")
        except TypeError:
            self.print_to_dialogue("Couldn't connect to Red Pitaya Sigma")
            
        try:
            self.rp_pi = scpi.Redpitaya("rp-f08a95.local")
            self.print_to_dialogue("Connected to Red Pitaya Pi")
        except TypeError:
            self.print_to_dialogue("Couldn't connect to Red Pitaya Pi")
        
        self.connectOPX()


if __name__ == "__main__":
    app = QApplication([])
    simulation = False if os.getlogin() == 'orelb' else True
    window = STIRAP_gui(simulation=simulation)
    window.show()
    app.exec_()
    sys.exit(app.exec_())

