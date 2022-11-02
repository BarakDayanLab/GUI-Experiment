# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1308, 753)
        self.horizontalLayout = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = QtWidgets.QFrame(Form)
        self.frame.setEnabled(False)
        self.frame.setFrameShape(QtWidgets.QFrame.WinPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.gridLayout = QtWidgets.QGridLayout(self.frame)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout_mpl = QtWidgets.QGridLayout()
        self.verticalLayout_mpl.setObjectName("verticalLayout_mpl")
        self.gridLayout.addLayout(self.verticalLayout_mpl, 0, 0, 1, 2)
        self.frame_3 = QtWidgets.QFrame(self.frame)
        self.frame_3.setMaximumSize(QtCore.QSize(16777215, 90))
        self.frame_3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_3.setObjectName("frame_3")
        self.label = QtWidgets.QLabel(self.frame_3)
        self.label.setGeometry(QtCore.QRect(310, 30, 321, 31))
        font = QtGui.QFont()
        font.setPointSize(22)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.frame_3, 1, 0, 1, 2)
        self.horizontalLayout.addWidget(self.frame)
        self.frame_2 = QtWidgets.QFrame(Form)
        self.frame_2.setMinimumSize(QtCore.QSize(290, 0))
        self.frame_2.setMaximumSize(QtCore.QSize(0, 16777215))
        self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.frame_6 = QtWidgets.QFrame(self.frame_2)
        self.frame_6.setMinimumSize(QtCore.QSize(290, 0))
        self.frame_6.setMaximumSize(QtCore.QSize(290, 16777215))
        self.frame_6.setFrameShape(QtWidgets.QFrame.WinPanel)
        self.frame_6.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.frame_6.setObjectName("frame_6")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.frame_6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.frame_4 = QtWidgets.QFrame(self.frame_6)
        self.frame_4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_4.setObjectName("frame_4")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.frame_4)
        self.gridLayout_2.setContentsMargins(3, 9, 3, 9)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.label_2 = QtWidgets.QLabel(self.frame_4)
        self.label_2.setObjectName("label_2")
        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 1)
        self.lineEdit_Folder = QtWidgets.QLineEdit(self.frame_4)
        self.lineEdit_Folder.setObjectName("lineEdit_Folder")
        self.gridLayout_2.addWidget(self.lineEdit_Folder, 0, 1, 1, 1)
        self.pushButtonBrowse = QtWidgets.QPushButton(self.frame_4)
        self.pushButtonBrowse.setCheckable(False)
        self.pushButtonBrowse.setAutoDefault(False)
        self.pushButtonBrowse.setDefault(False)
        self.pushButtonBrowse.setFlat(False)
        self.pushButtonBrowse.setObjectName("pushButtonBrowse")
        self.gridLayout_2.addWidget(self.pushButtonBrowse, 0, 2, 1, 1)
        self.pushButton_get_temperature_fromFolder = QtWidgets.QPushButton(self.frame_4)
        self.pushButton_get_temperature_fromFolder.setEnabled(False)
        self.pushButton_get_temperature_fromFolder.setObjectName("pushButton_get_temperature_fromFolder")
        self.gridLayout_2.addWidget(self.pushButton_get_temperature_fromFolder, 2, 0, 1, 3)
        self.label_7 = QtWidgets.QLabel(self.frame_4)
        self.label_7.setAlignment(QtCore.Qt.AlignCenter)
        self.label_7.setObjectName("label_7")
        self.gridLayout_2.addWidget(self.label_7, 1, 0, 1, 1)
        self.lineEdit_3 = QtWidgets.QLineEdit(self.frame_4)
        self.lineEdit_3.setObjectName("lineEdit_3")
        self.gridLayout_2.addWidget(self.lineEdit_3, 1, 1, 1, 1)
        self.verticalLayout.addWidget(self.frame_4)
        self.frame_temperature = QtWidgets.QFrame(self.frame_6)
        self.frame_temperature.setEnabled(False)
        self.frame_temperature.setMinimumSize(QtCore.QSize(268, 0))
        self.frame_temperature.setMaximumSize(QtCore.QSize(290, 126))
        self.frame_temperature.setFrameShape(QtWidgets.QFrame.WinPanel)
        self.frame_temperature.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_temperature.setObjectName("frame_temperature")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.frame_temperature)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.lineEdit = QtWidgets.QLineEdit(self.frame_temperature)
        self.lineEdit.setObjectName("lineEdit")
        self.gridLayout_3.addWidget(self.lineEdit, 2, 3, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.frame_temperature)
        self.label_4.setAlignment(QtCore.Qt.AlignCenter)
        self.label_4.setObjectName("label_4")
        self.gridLayout_3.addWidget(self.label_4, 0, 0, 1, 1)
        self.doubleSpinBox_start_temp = QtWidgets.QDoubleSpinBox(self.frame_temperature)
        self.doubleSpinBox_start_temp.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.doubleSpinBox_start_temp.setProperty("value", 1.0)
        self.doubleSpinBox_start_temp.setObjectName("doubleSpinBox_start_temp")
        self.gridLayout_3.addWidget(self.doubleSpinBox_start_temp, 2, 0, 1, 1)
        self.doubleSpinBox_end_temp = QtWidgets.QDoubleSpinBox(self.frame_temperature)
        self.doubleSpinBox_end_temp.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.doubleSpinBox_end_temp.setProperty("value", 15.0)
        self.doubleSpinBox_end_temp.setObjectName("doubleSpinBox_end_temp")
        self.gridLayout_3.addWidget(self.doubleSpinBox_end_temp, 2, 1, 1, 1)
        self.spinBox_N_temp = QtWidgets.QSpinBox(self.frame_temperature)
        self.spinBox_N_temp.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.spinBox_N_temp.setMinimum(1)
        self.spinBox_N_temp.setMaximum(30)
        self.spinBox_N_temp.setProperty("value", 14)
        self.spinBox_N_temp.setObjectName("spinBox_N_temp")
        self.gridLayout_3.addWidget(self.spinBox_N_temp, 2, 2, 1, 1)
        self.label_5 = QtWidgets.QLabel(self.frame_temperature)
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName("label_5")
        self.gridLayout_3.addWidget(self.label_5, 0, 1, 1, 1)
        self.pushButton_measure_temperature = QtWidgets.QPushButton(self.frame_temperature)
        self.pushButton_measure_temperature.setMinimumSize(QtCore.QSize(79, 0))
        self.pushButton_measure_temperature.setObjectName("pushButton_measure_temperature")
        self.gridLayout_3.addWidget(self.pushButton_measure_temperature, 3, 0, 1, 4)
        self.label_8 = QtWidgets.QLabel(self.frame_temperature)
        self.label_8.setAlignment(QtCore.Qt.AlignCenter)
        self.label_8.setObjectName("label_8")
        self.gridLayout_3.addWidget(self.label_8, 0, 3, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.frame_temperature)
        self.label_6.setAlignment(QtCore.Qt.AlignCenter)
        self.label_6.setObjectName("label_6")
        self.gridLayout_3.addWidget(self.label_6, 0, 2, 1, 1)
        self.progressBar = QtWidgets.QProgressBar(self.frame_temperature)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout_3.addWidget(self.progressBar, 4, 0, 1, 4)
        self.verticalLayout.addWidget(self.frame_temperature)
        self.listWidget_dialogue = QtWidgets.QListWidget(self.frame_6)
        self.listWidget_dialogue.viewport().setProperty("cursor", QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.listWidget_dialogue.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.listWidget_dialogue.setAutoScrollMargin(16)
        self.listWidget_dialogue.setDragEnabled(False)
        self.listWidget_dialogue.setAlternatingRowColors(True)
        self.listWidget_dialogue.setObjectName("listWidget_dialogue")
        self.verticalLayout.addWidget(self.listWidget_dialogue)
        self.pushButton_temperature_Connect = QtWidgets.QPushButton(self.frame_6)
        self.pushButton_temperature_Connect.setObjectName("pushButton_temperature_Connect")
        self.verticalLayout.addWidget(self.pushButton_temperature_Connect)
        self.verticalLayout_3.addWidget(self.frame_6)
        self.horizontalLayout.addWidget(self.frame_2)

        self.retranslateUi(Form)
        self.pushButtonBrowse.clicked.connect(Form.browseSlot)
        self.lineEdit_Folder.returnPressed.connect(Form.returnPressedSlot)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label.setText(_translate("Form", "Temperature:"))
        self.label_2.setText(_translate("Form", "Folder name"))
        self.pushButtonBrowse.setText(_translate("Form", "Browse"))
        self.pushButton_get_temperature_fromFolder.setText(_translate("Form", "Get Temperature"))
        self.label_7.setToolTip(_translate("Form", "Pixel/length calibration in pixels per milimiter"))
        self.label_7.setText(_translate("Form", "Cal (pixel/mm)"))
        self.label_4.setText(_translate("Form", "Start (ms)"))
        self.label_5.setText(_translate("Form", "End (ms)"))
        self.pushButton_measure_temperature.setText(_translate("Form", "Measure Temperature"))
        self.label_8.setToolTip(_translate("Form", "Pixel/length calibration in pixels per milimiter"))
        self.label_8.setText(_translate("Form", "Cal (pixel/mm)"))
        self.label_6.setText(_translate("Form", "N points"))
        self.pushButton_temperature_Connect.setText(_translate("Form", "Connect"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())