import logging
from vxi11 import Instrument
import numpy as np


class Scope(Instrument):
    """
    This class is a wrapper for the vxi11.Instrument class. It adds some useful methods for the scope.

    Attributes:
    ----------
        id (str): The scope's ID.
        scope_type (str): The scope's type.

    Methods:
    --------
        __init__(ip: str): Initializes the scope.
        get_data(channel: int): Returns the data from the specified channel.
    """
    def __init__(self, ip: str):
        super().__init__(ip)
        self.write('*CLS')  # clear EVERYTHING!
        self.write('WFMOUTPRE:ENCDG ASCii')  # send back data in ascii
        self.id = self.ask("*IDN?")

        if 'TEKTRONIX,DPO7254' in self.id:
            self.scope_type = 'DPO7254'
        elif 'TEKTRONIX,DPO70604' in self.id:
            self.scope_type = 'DPO70604'
        else:
            raise Exception("Scope type not recognized")

        self.num_data_points = 0

    def get_data(self, channel: int):
        try:
            self.write(f'DATA:SOURCE CH{channel}')
            source = self.ask('DATA:SOURCE?')

            # First we get back a few acquisition parameters
            acq_params = self.ask('WFMOutpre?').split(';')
            # make sure we are working with seconds and volts scale;
            # if this line raises an error, scope must be returning other units
            if acq_params[8] != '"s"' or acq_params[-5] != '"V"':
                logging.error('Error reading from scope. make sure all the required channels are on.')

            # number of points in data; Time scale multiplier
            self.num_data_points, time_multiplier = int(acq_params[6]), float(acq_params[9])

            # Digital (arbitrary) scale to volts. multiplier, arbitrary offset, offset in volts
            y_multiplier, y_digital_off, y_offset = float(acq_params[-4]), float(acq_params[-3]), float(acq_params[-2])

            # make sure we bring back entire data
            self.write(f'DATA:STOP {self.num_data_points * 2}')

            # acquire data
            data_string = self.ask('CURVE?')
            # create timescale
            time_data = np.linspace(0, self.num_data_points * time_multiplier, self.num_data_points)
            # data string to numpy array
            data = np.fromstring(data_string, dtype=int, sep=',')
            # convert to volts
            # TODO: check about the offset
            waveform = (data - y_digital_off) * y_multiplier
            if self.ask('*ESR?') != '0':
                logging.error(f'Error reading from scope. Acquisition from {source} failed')

            return time_data, waveform

        except Exception as e:
            print(e)
            return None, None


class FakeScope:
    def __init__(self, channels_dict: dict):
        self.channels_dict = channels_dict
        self.data = {channels_dict["transmission"]: np.load("transmission.npy"),
                     channels_dict["rubidium"]: np.load("rubidium.npy")
                     }
        self.num_data_points = self.data[channels_dict["transmission"]].shape[1]
        self.time_axis = np.linspace(0, 100, self.num_data_points)
        self.current_idx = {channels_dict["transmission"]: 0,
                            channels_dict["rubidium"]: 0}

    def get_data(self, channel: int):
        data = self.data[channel][self.current_idx[channel]]
        self.current_idx[channel] += 1
        return self.time_axis, data
