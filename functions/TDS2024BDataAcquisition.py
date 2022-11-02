import vxi11  # https://github.com/python-ivi/python-vxi11
import numpy as np
import matplotlib.pyplot as plt
from datetime import date, datetime
import time
import os
from os import listdir
from os.path import isfile, join
from lorentizansFit import multipleLorentziansFitter
from scipy.fft import rfft, rfftfreq, irfft  # from signal cleanup
import pyvisa

# TDS programming manual:
# https://download.tek.com/manual/TBS1000-B-EDU-TDS2000-B-C-TDS1000-B-C-EDU-TDS200-TPS2000-B-Programmer-077044403_RevB.pdf
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def printError(s=''): print(f"{bcolors.WARNING}{s}{bcolors.ENDC}")


def printGreen(s=''): print(f"{bcolors.OKGREEN}{s}{bcolors.ENDC}")


class TDS2024Visa():
    def __init__(self, port = 'USB0::0x0699::0x036A::C047935::INSTR'):
        self.rm = pyvisa.ResourceManager()
        try:
            self.scope = self.rm.open_resource(port)
            printGreen('Connected to ' + str(self.scope.query('*IDN?')))
        except Exception as e:
            printError('Cold not connect to %s. Try another port. \n %s' % (port,e))
            for s in self.rm.list_resources():
                try:
                    print('%s identifies as: ' % str(s) ,self.rm.open_resource(str(s)).query('*IDN?'))
                except:
                    printError('Could not identify %s' %str(s))
            return

        self.write('*CLS')  # clear EVERYTHING!
        self.ID = self.ask("*IDN?")
        self.dataString = ''
        self.wvfm = [[]] * 5  # assuming channels 1-4
        if 'TEKTRONIX,TDS 2024B' not in self.ID:
            printError('Could not identify instrument. Check connection, try again.')
            return
        printGreen(self.ID)

    # Following are two scriptting shortcuts
    def ask(self, s):
        return (self.scope.query(s))

    def write(self, s):
        self.scope.write(s)

    # Acquire data from a specific channel
    def acquireData(self, chns=(1, 2, 3, 4)):
        for ch in chns:
            if ch not in [1, 2, 3, 4]:
                printError('Wrong channel!')
                return

            self.write('DAT:ENC ASCii')  # send back data in ascii
            self.write('DATA:SOURCE CH{}'.format(int(ch)))
            self.source = self.ask('DATA:SOURCE?')

            # First we get back a few acquistion parameters
            aParams = self.ask('WFMPre?').split(';')
            assert aParams[-5] == '"s"' and '"Volts"' in aParams[-1]   # make sure we are working with seconds and volts scale; if this line raises an error, scope must be returning other units
            nDataPoints, xMulti = int(aParams[5]), float(aParams[6].split()[5])  # number of points in WVFM; Time scale multiplier
            yMult, yDigOff, yOffset = float(aParams[-4]), float(aParams[-3]), float(aParams[-2])  # Digital (arbitrary) scale to volts. multiplier, arbitrary offset, offset in volts
            self.write('DATA:STOP {}'.format(nDataPoints * 2))  # make sure we bring back entire data
            # Acquisition
            dataString = self.ask('CURVE?')  # acquire data
            self.timeData = np.linspace(start=0, stop=nDataPoints * xMulti, num=nDataPoints)  # create time scale
            self.wvfm[ch] = (np.fromstring(dataString, dtype=int, sep=',') - yDigOff) * yMult  # get data in volts
            if self.ask('*ESR?') == '0\n':  # check for error codes etc. If all is right, answer should be 0
                printGreen('Acquisition from {} successful'.format(self.source))
            else:
                printError('Acquisition from {} failed'.format(self.source))

    # Plot last received data
    def plotData(self, chns=1, show=True):
        now = datetime.now()
        nowformated = now.strftime("%m/%d/%Y, %H:%M:%S")
        if type(chns) is list:
            for ch in chns:
                plt.plot(self.timeData, self.wvfm[ch])
        else:
            plt.plot(self.timeData, self.wvfm[chns])
        plt.xlabel('Time [sec]')
        plt.ylabel('Voltage [V]')
        plt.title(str(self.source) + '\n%s' % str(nowformated))
        plt.grid(True)
        if show:
            plt.show()

    def saveData(self, filename=''):
        if filename != '':
            filename = str(filename) + ' - '
        now = datetime.now()
        today = date.today()
        datadir = os.path.join("U:\\", "Lab_2021-2022", "DATA", "TDS2024B")
        todayformated = today.strftime("%Y-%m-%d")
        todaydatadir = os.path.join(datadir, todayformated)
        nowformated = now.strftime("%Hh%Mm%Ss")
        try:
            os.makedirs(todaydatadir)
            print("Created folder DATA/TDS2024B/%s" % (todayformated))
        except FileExistsError:
            pass

        try:
            nowformated = now.strftime("%H-%M-%S") + filename

            self.datafile = os.path.join(filename, todaydatadir, nowformated + ".txt")
            meta = "Traces from the TDS2024B scope, obtained on %s at %s.\n" % (todayformated, nowformated)
            np.savez_compressed(os.path.join(todaydatadir, nowformated), Ch_1_Data=self.wvfm[1],
                                Ch_2_Data=self.wvfm[2], Ch_3_Data=self.wvfm[3], Ch_4_Data=self.wvfm[4], time=self.timeData,
                                meta=meta)
            print('Data saved, {}'.format(nowformated))
        except Exception as e:
            printError('Error saving data at {time}: {e}'.format(time=nowformated, e=e))



# interval = 60  # 1 minutes
def saveDataEveryTimeInterval(scope, chns = [1,2,3,4],interval = 60):
    while True:
        scope.acquireData(chns=chns)
        scope.saveData()
        time.sleep(interval)

def savePlotsAndData(filename=''):
    if filename != '':
        filename = ' - ' + str(filename)
    plt.clf()  # clear all existing figures.
    # ------ Data acquire ------
    scope.acquireData(chns=(1, 2, 3))
    scope.saveData(filename = filename)
    # ------ Plot ------------
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    nowformated = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    plt.title(filename)

    ax1.plot(scope.timeData, scope.wvfm[1], color='g')
    # ax1.set_ylabel('Temperature [K]', color='b')
    ax1.set_xlabel('Time')
    ax2.plot(scope.timeData, scope.wvfm[2], color='b')
    # ax2.set_ylabel('Detuning [GHz], of F2->F\'3', color='r')
    # ax2.invert_yaxis()
    plt.grid()

    # plt.scatter(x = scope.timeData[lf.peaks_indices], y = scope.wvfm[lf.peaks_indices],color='black')

    # ----- Date-Time & Path ------
    # TODO: Remove code duplicacy with save above...
    datadir = os.path.join("U:\\", "Lab_2021-2022", "DATA", "DPO7254")
    now = datetime.now()
    today = date.today()
    todayformated = today.strftime("%B-%d-%Y")
    todaydatadir = os.path.join(datadir, todayformated)
    try:
        os.makedirs(todaydatadir)
        print("Created folder DATA/FPO7254/%s" % (todayformated))
        print("Figure Saved")
    except FileExistsError:
        print("Figure Saved")

    nowformated = now.strftime("%H-%M-%S") + filename

    figPath = os.path.join(todaydatadir, nowformated + ".png")
    plt.savefig(figPath, dpi=300, format='png', pad_inches=0.1)
    plt.close('all')


def dataStringToDatetime(s):
    date_time_obj = datetime.strptime(s, '%B-%d-%Y %Hh%Mm%Ss')
    return (date_time_obj)


defDirectory = 'U:\\Lab_2021-2022\\DATA\\TDS2024B\\'


def loadData(file):
    npData = np.load(file)
    ch1, ch2, ch3, ch4 = npData['Ch_1_Data'], npData['Ch_2_Data'], npData['Ch_3_Data'], npData['Ch_4_Data']
    time = npData['time']
    return (time, ch1, ch2, ch3, ch4)


def listFilesInDirectory(dire, extenstion=None):
    onlyfiles = None
    if type(extenstion) is str:
        onlyfiles = [f for f in listdir(dire) if (isfile(join(dire, f)) and f.endswith(extenstion))]
    else:
        onlyfiles = [f for f in listdir(dire) if isfile(join(dire, f))]

    return onlyfiles



def analyzeFiles():
    # dateTimeLimit = (dataStringToDatetime('March-14-2022 11h25m28s'),dataStringToDatetime('March-16-2022 11h25m28s'))
    dateTimeLimit = (dataStringToDatetime('March-13-2022 00h25m28s'), dataStringToDatetime('March-16-2022 11h25m28s'))
    dates = ['March-13-2022', 'March-14-2022']
    msrmntTime, temps, detunings, detuning_coeffs = [], [], [], []
    # dates = ['March-14-2022']
    for date in dates:
        for file in listFilesInDirectory(defDirectory + date, extenstion='.npz'):
            try:
                dateTime = dataStringToDatetime('%s %s' % (
                    date, file.replace('.npz', '')))  # date + file should look something like 'March-13-2022 00h15m28s'
                if dateTime > max(dateTimeLimit) or dateTime < min(dateTimeLimit): continue
                f = defDirectory + date + '\\' + file
                time, ch1, ch2, ch3, ch4 = loadData(f)
                # ---- find peaks ----
                RbPeaks, properties = find_peaks(ch1, prominence=0.001)
                ResPeaks, _ = find_peaks(ch2 * (-1), prominence=0.1)
                numberOfDetectedPeaks = 8  # should detect exactly 8 peaks. otherwise, vortex probably moved
                if len(RbPeaks) != numberOfDetectedPeaks:
                    print('Found more than %d Rb peaks! File: %s' % (numberOfDetectedPeaks, file))
                    continue  # skip current file
                if len(ResPeaks) != 1:
                    print('Problem detecting resonance in file: %s' % file)
                    continue  # skip current file
                # --- plot -----
                ##            plt.plot(time, ch1)
                ##            plt.plot(time, ch2)
                ##            plt.plot(time[RbPeaks][0], ch1[RbPeaks][0], "x")
                ##            plt.plot(time[RbPeaks][-1], ch1[RbPeaks][-1], "x")
                ##            plt.plot(time[RbPeaks][2], ch1[RbPeaks][2], "x")
                ##            plt.plot(time[ResPeaks], ch2[ResPeaks], "x")
                ##            plt.show()

                # -- detuning ---
                c = 6.8347 / (time[RbPeaks][-1] - time[RbPeaks][0])  # GHz / sec
                detuning = c * (time[ResPeaks][0] - time[RbPeaks][2])  # in [Ghz]
                msrmntTime.append(dateTime)
                T_R, R = wvfmToTemp(ch3)
                temps.append(T_R)
                detunings.append(detuning)
                detuning_coeffs.append(c)
            except:
                # printError('Could not analyze file: %s' % f)
                pass

    return (msrmntTime, temps, detunings, detuning_coeffs)


# time, ch1, ch2, ch3, ch4 = loadData(file)
def analyzeAndPlotFiles():
    msrmntTime, temps, detunings, detuning_coeffs = analyzeFiles()

    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    ax1.plot(msrmntTime, temps, '.', color='b')
    plt.title('Temperature [K] & Detuning [GHz] vs. Time')
    ax1.set_ylabel('Temperature [K]', color='b')
    ax1.set_xlabel('Time')
    ax2.plot(msrmntTime, detunings, '.', color='r')
    ax2.set_ylabel('Detuning [GHz], of F2->F\'3', color='r')
    ax2.invert_yaxis()
    plt.grid()
    plt.show()


# analyzeAndPlotFiles()
#
# while(True):
#     savePlotsAndTemperatureData()
# plt.show()
# savePlotsAndData(filename='Q6_R101_779.4_100mVpp_S')
s = TDS2024Visa()

# s.acquireData(chns=[4])
# aomPlus = s.wvfm[4]
# input('move det')
# s.acquireData(chns=[4])
# aomMinus = s.wvfm[4]
#
# plt.plot(s.timeData, aomMinus)
# plt.plot(s.timeData, aomPlus)
#
# plt.xlabel('Time [sec]')
# plt.ylabel('Voltage [V]')
# plt.grid(True)
# plt.show()
#
# a = aomPlus
# b = aomMinus * np.max(aomPlus)/np.max(aomMinus)
