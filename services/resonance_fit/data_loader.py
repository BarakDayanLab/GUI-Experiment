from .scope_connection import Scope, FakeScope
from functions.RedPitayaWebsocket import Redpitaya
from threading import Thread
from multiprocessing import Queue
import time


class DataLoader:
    def __init__(self):
        self.thread = Thread(target=self.load_data, daemon=True)
        self.queue = Queue(2)
        self.stop = False

    def load_data(self):
        pass

    def put_data_to_queue(self, data):
        if self.queue.full():
            self.queue.get()
        self.queue.put(data)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop = True
        self.thread.join()
        while not self.queue.empty():
            self.queue.get()
        self.queue.join()


class ScopeDataLoader(DataLoader):
    def __init__(self, channels_dict: dict, scope_ip='132.77.54.241', wait_time=0.1):
        super().__init__()
        self.scope = Scope(ip=scope_ip) if scope_ip is not None else FakeScope(channels_dict)
        self.channels_dict = channels_dict
        self.wait_time = wait_time

    def load_data(self):
        while not self.stop:
            try:
                channel_number = self.channels_dict["rubidium"]
                _, rubidium_spectrum = self.scope.get_data(channel_number)

                channel_number = self.channels_dict["transmission"]
                _, transmission_spectrum = self.scope.get_data(channel_number)

                self.put_data_to_queue((rubidium_spectrum, transmission_spectrum))
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


            # self.red_pitaya.set_outputFunction(output=1, function=str(self.outputsFrame.comboBox_ch1OutFunction.currentText()))
            # self.red_pitaya.set_outputFunction(output=2, function=str(self.outputsFrame.comboBox_ch2OutFunction.currentText()))
            # self.red_pitaya.set_outputAmplitude(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutAmp.value()))
            # self.red_pitaya.set_outputAmplitude(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutAmp.value()))
            # self.red_pitaya.set_outputFrequency(output=1, freq=float(self.outputsFrame.doubleSpinBox_ch1OutFreq.value()))
            # self.red_pitaya.set_outputFrequency(output=2, freq=float(self.outputsFrame.doubleSpinBox_ch2OutFreq.value()))
            # self.red_pitaya.set_outputOffset(output=1, v=float(self.outputsFrame.doubleSpinBox_ch1OutOffset.value()))
            # self.red_pitaya.set_outputOffset(output=2, v=float(self.outputsFrame.doubleSpinBox_ch2OutOffset.value()))
            self.configure_input_channels()

        self.put_data_to_queue(data)

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
        print(message)
