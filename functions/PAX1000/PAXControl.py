import time
import math
import numpy as np
import pyvisa


class PAXControl:

    def __init__(self, port='ASRL7::INSTR'):
        self.rm = pyvisa.ResourceManager()
        resources = self.rm.list_resources()
        port = 'USB0::0x1313::0x8031::M00817173::INSTR'
        try:
            self.inst = self.rm.open_resource(port)
            time.sleep(1)
            idn = self.inst.query('*IDN?')

            self.log('Connected to ' + str(self.inst.query('*IDN?')))  # Instrument Identification Code
        except Exception as err:
            self.log('Could not connect to %s. Try another port.' % port)
            for s in self.rm.list_resources():
                try:
                    self.log('%s identifies as: %s' % (str(s), self.rm.open_resource(str(s)).query('*IDN?')))
                except:
                    self.log('Could not identify %s' % str(s))
        self.current_channel = None

    def readSomething(self):
        # Measurement in mode 9
        self.inst.write('SENS:CALC 9;:INP:ROT:STAT 1')

        # See here: https://www.mathworks.com/matlabcentral/answers/406668-connecting-to-thorlabs-pax1000-polarimeter-using-test-measurement-tool
        lat_str_values = self.inst.query('SENS:DATA:LAT?')
        values = np.asarray(lat_str_values.split(','), dtype=float)

        mode = int(values[2])
        az = values[9]*180/np.pi  # In degrees
        ellip = values[10] * 180 / np.pi  # in degrees
        DOP = values[11] * 100  # in (degree of polarization)
        P = values[12] * 1e3  # in mW

        # Compute normalized Stokes parameters
        Psi = values[9]
        Chi = values[10]
        S1 = math.cos(2 * Psi) * math.cos(2 * Chi)  # normalized S1
        S2 = math.sin(2 * Psi) * math.cos(2 * Chi)  # normalized S2
        S3 = math.sin(2 * Chi)  # normalized S3

        pass

    def log(self, msg):
        print(msg)
        #printGreen(msg)

if __name__ == "__main__":

    pc = PAXControl()
    pc.readSomething()
    pass