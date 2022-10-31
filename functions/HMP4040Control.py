#Here is an example usage (it will read all unique settings into a list, reset the instrument and then program the unique settings back into the instrument):

import time
import pyvisa

# DPO programming manual:
# https://download.tek.com/manual/MSO-DPO5000-DPO7000-DPO70000-DX-SX-DSA70000-and-MSO70000-DX-Programmer-077001025.pdf
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

def printError(s = ''): print(f"{bcolors.WARNING}{s}{bcolors.ENDC}")
def printGreen(s = ''): print(f"{bcolors.OKGREEN}{s}{bcolors.ENDC}")



class HMP4040Visa():
    def __init__(self, port = 'ASRL5::INSTR'):
        self.rm = pyvisa.ResourceManager()
        try:
            self.inst = self.rm.open_resource(port)
            time.sleep(2)
            printGreen('Connected to ' + str(self.inst.query('*IDN?')))
        except:
            printError('Cold not connect to %s. Try another port.' % port)
            for s in self.rm.list_resources():
                try:
                    print('%s identifies as: ' % str(s) ,self.rm.open_resource(str(s)).query('*IDN?'))
                except:
                    printError('Could not identify %s' %str(s))

    # returns power in Watts
    def setOutput(self, ch = 4):
        self.inst.write('INST OUT%s' % str(int(ch)))
        printGreen('Channel set to %s'%str(int(ch)))
        return(float(ch))

    def setVoltage(self, v = 0):
        voltage = self.inst.write('VOLT %.3f' % float(v))
        return(float(voltage))
    def setCurrent(self, I = 0):
        voltage = self.inst.write('CURR %.3f' % float(I))
        return(float(voltage))

    def outputState(self, state = 2):
        #print('OUTP:SEL %s' % int(state / 2))
        self.inst.write('OUTP:SEL %s' % int(state / 2))
        return (float(state))

    def getCurrent(self):
        cur = self.inst.query('CURR?')
        return(float(cur))

    def getVoltage(self):
        v = self.inst.query('VOLT?')
        return(float(v))

#h = HMP4040Visa()