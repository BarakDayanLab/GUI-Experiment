# -*- coding: utf-8 -*-
"""
@author: Jeremy Raskop
Created on Fri Dec 25 14:16:30 2020

"""

from PyQt5 import uic
from PyQt5.QtWidgets import QTabWidget, QGridLayout, QMainWindow, QApplication
from PyQt5.QtCore import QThreadPool
import os
from widgets.pgc import pgcWidget
from widgets.temperature import temperatureWidget
from widgets.od import ODWidget
from widgets.STIRAP import STIRAPWidget
from widgets.config_OPX import configWidget
from widgets.MWSpectro import MWSpectroWidget
import sys
sys._excepthook = sys.excepthook


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = exception_hook


class Experiment_gui(QMainWindow):
    def __init__(self, simulation=True):
        super(Experiment_gui, self).__init__()
        ui = os.path.join(os.path.dirname(__file__), "main_GUI.ui")
        uic.loadUi(ui, self)
        
        # Add a tab widget:
        layout = QGridLayout()
        self.mainframe.setLayout(layout)
        self.mainframe.setContentsMargins(0,0,0,0)
        self.tabwidget = QTabWidget()
        self.tabwidget.setTabsClosable(False)
        self.tabwidget.setMovable(True)
        self.tabwidget.tabCloseRequested.connect(self.removeTab)
        # self.tabwidget.currentChanged.connect(self.tabchanged)
        layout.addWidget(self.tabwidget, 0, 0)
        layout.setContentsMargins(5,0, 5, 0)
        self.OPX = None
        
        # Open widgets upon called action:
        self.actionPGC.triggered.connect(self.pgc_open_tab)
        self.actionTemperature.triggered.connect(self.temperature_open_tab)
        self.actionOD.triggered.connect(self.OD_open_tab)
        self.actionConfigure.triggered.connect(self.conf_open_tab)
        self.actionSTIRAP.triggered.connect(self.STIRAP_open_tab)
        self.actionMW_Spectroscopy.triggered.connect(self.MW_open_tab)

        # Start Threadpool for multi-threading 
        self.simulation = simulation
        if __name__ == "__main__":
            self.threadpool = QThreadPool()
            print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

    def STIRAP_open_tab(self):
        if not hasattr(self, 'OD_tab'):
            self.STIRAP_tab = STIRAPWidget.STIRAP_gui(Parent=self, simulation=self.simulation)
            self.STIRAP_tab.threadpool = self.threadpool
            self.tabwidget.addTab(self.STIRAP_tab, "STIRAP")
            if self.OPX is not None :
                self.STIRAP_tab.enable_interface(True)
                self.STIRAP_tab.OPX = self.OPX

    def MW_open_tab(self):
        self.MW_spectro_tab = MWSpectroWidget.MWSpectroWidget(Parent=self, simulation=self.simulation)
        self.MW_spectro_tab.threadpool = self.threadpool
        self.tabwidget.addTab(self.MW_spectro_tab, "MWSpectro")
        if self.OPX is not None:
            self.MW_spectro_tab.enable_interface(True)
            self.MW_spectro_tab.OPX = self.OPX

    def pgc_open_tab(self):
        if not hasattr(self, 'pgc_tab'):
            self.pgc_tab = pgcWidget.Pgc_gui(Parent=self, simulation=self.simulation)
            self.pgc_tab.threadpool = self.threadpool
            self.tabwidget.addTab(self.pgc_tab, "PGC")
            if self.OPX is not None:
                self.pgc_tab.enable_interface(True)
                self.pgc_tab.OPX = self.OPX

    def temperature_open_tab(self):
        if not hasattr(self, 'temperature_tab'):
            self.temperature_tab = temperatureWidget.Temperature_gui(Parent=self, simulation=self.simulation)
            self.temperature_tab.threadpool = self.threadpool
            self.tabwidget.addTab(self.temperature_tab, "Temperature")
            if self.OPX is not None :
                self.temperature_tab.enable_interface(True)
                self.temperature_tab.OPX = self.OPX

    def OD_open_tab(self):
        if not hasattr(self, 'OD_tab'):
            self.OD_tab = ODWidget.OD_gui(Parent=self, simulation=self.simulation)
            self.OD_tab.threadpool = self.threadpool
            self.tabwidget.addTab(self.OD_tab, "OD/Nat")
            if self.OPX is not None :
                self.OD_tab.enable_interface(True)
                self.OD_tab.OPX = self.OPX

    def conf_open_tab(self):
        if not hasattr(self, 'conf_tab'):
            # self.conf_tab = configWidget.ConfigGUI(Parent=self, simulation=self.simulation)
            self.conf_tab = configWidget.ConfigGUI()
            self.conf_tab.threadpool = self.threadpool
            self.tabwidget.addTab(self.conf_tab, "Configure")

    def removeTab(self, index):
        widget = self.tabwidget.widget(index)
        if widget is not None:
            widget.deleteLater()
            if widget.objectName() == 'Temperature':
                del self.temperature_tab
            if widget.objectName() == 'PGC':
                del self.pgc_tab
        self.tabwidget.removeTab(index)


if __name__ == "__main__":
    import sys
    app = QApplication([])
    simulation = False if os.getlogin() == 'orelb' else True
    window = Experiment_gui(simulation=simulation)
    window.show()
    app.exec_()
    # sys.exit(app.exec_())

