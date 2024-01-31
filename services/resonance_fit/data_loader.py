from .scope_connection import Scope, FakeScope
from functions.RedPitayaWebsocket import Redpitaya
from threading import Thread
from multiprocessing import Queue
import time


class DataLoader:
    def __init__(self):
        self.thread = Thread(target=self.load_data, daemon=True)
        self.is_stopped = False
        self.on_data_callback = lambda data: None

    def update(self, params):
        pass

    def load_data(self):
        pass

    def start(self):
        self.thread.start()

    def stop(self):
        self.is_stopped = True
        self.thread.join()


class ScopeDataLoader(DataLoader):
    def __init__(self, channels_dict: dict, scope_ip='132.77.54.241', wait_time=0.1):
        super().__init__()
        self.scope = Scope(ip=scope_ip) if scope_ip is not None else FakeScope(channels_dict)
        self.channels_dict = channels_dict
        self.wait_time = wait_time

    def load_data(self):
        while not self.is_stopped:
            try:
                channel_number = self.channels_dict["rubidium"]
                _, rubidium_spectrum = self.scope.get_data(channel_number)

                channel_number = self.channels_dict["transmission"]
                _, transmission_spectrum = self.scope.get_data(channel_number)

                self.on_data_callback((rubidium_spectrum, transmission_spectrum))
                time.sleep(self.wait_time)
            except Exception as e:
                print(e)
                time.sleep(self.wait_time)


class DataLoaderRedPitaya(DataLoader):
    def __init__(self, host="rp-ffffb4.local"):
        super().__init__()
        self.config = {'locker': 'cavity'}
        self.red_pitaya = Redpitaya(host,
                                    got_data_callback=self.got_data,
                                    dialogue_print_callback=self.dialogue_print_callback,
                                    config=self.config)

        if not self.red_pitaya.connected:
            self.red_pitaya.close()
            self.red_pitaya = Redpitaya(host,
                                        got_data_callback=self.got_data,
                                        dialogue_print_callback=self.dialogue_print_callback,
                                        config=self.config)

        if not self.red_pitaya.connected:
            self.red_pitaya.close()
            raise Exception("Red Pitaya not connected")

    def stop(self):
        self.red_pitaya.close()
        super().stop()

    def update(self, params):
        """
        Update the Red Pitaya parameters

        Parameters:
            params {dict} -- The parameters to update the Red Pitaya. The dictionary should contain the following keys:
                offset_1 {float} -- The offset of channel 1
                offset_2 {float} -- The offset of channel 2
                voltage_1 {float} -- The voltage of channel 1
                voltage_2 {float} -- The voltage of channel 2
                trigger_level {float} -- The trigger level
                trigger_delay {float} -- The trigger delay
        """
        self.red_pitaya.set_outputOffset(output=1, v=params["offset_1"])
        self.red_pitaya.set_outputOffset(output=2, v=params["offset_2"])
        self.red_pitaya.set_outputAmplitude(output=1, v=params["voltage_1"])
        self.red_pitaya.set_outputAmplitude(output=2, v=params["voltage_2"])
        self.red_pitaya.set_triggerLevel(params["trigger_level"], True)
        self.red_pitaya.set_triggerDelay(params["trigger_delay"], True)
        self.red_pitaya.updateParameters()

    def load_data(self):
        self.red_pitaya.run()

    def got_data(self, data, parameters):
        if self.red_pitaya.firstRun:
            self.red_pitaya.firstRun = False
            self.red_pitaya.set_triggerSource("EXT", True)
            self.red_pitaya.set_triggerSweep('NORMAL', True)
            self.red_pitaya.set_triggerSlope('FALLING', True)
            self.red_pitaya.set_triggerLevel(0.1, True)
            self.red_pitaya.set_triggerDelay(0, True)
            self.red_pitaya.set_inverseChannel(False, 1)
            self.red_pitaya.set_inverseChannel(False, 2)
            self.configure_input_channels()

        self.on_data_callback(data)

    def configure_input_channels(self):
        # Set channel 1
        self.red_pitaya.set_inputAcDcCoupling(1, "AC")
        self.red_pitaya.set_inputGain(1, "1:1")
        self.red_pitaya.set_inputState(1, True)

        # Set channel 2
        self.red_pitaya.set_inputAcDcCoupling(2, "AC")
        self.red_pitaya.set_inputGain(2, "1:1")
        self.red_pitaya.set_inputState(2, True)

    @staticmethod
    def dialogue_print_callback(message, color=""):
        pass
