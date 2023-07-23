import sys
import time
import ftd2xx as ftd
from pylablib.devices import Thorlabs

# See this site - https://iosoft.blog/2018/12/02/ftdi-python-part-1/

class MPC320Control:
    DEVICE_ID = '38133894'

    def __init__(self, device_id=None):

        if not device_id:
            device_id = self.DEVICE_ID

        # Check that the device id is in the list of Kinesis devices
        devices = Thorlabs.list_kinesis_devices()
        self.device = devices[0]

        # Get the device (aka stage)
        self.stage = Thorlabs.KinesisMotor(self.DEVICE_ID, is_rack_system=False)  # True
        return

    def open_via_ftd(self):
        zzz = ftd.open(0)  # Open first FTDI device
        device_info = zzz.getDeviceInfo()
        return device_info

    def test_move(self):
        #self.stage.set_default_channel(1)

        #z0 = self.stage.get_status(1)
        #jp = self.stage.get_jog_parameters(1)

        dir = '-'
        for z in range(4):
            self.stage.jog(direction=dir, channel=1, kind="builtin")
            time.sleep(0.4)
        #self.stage.home(sync=True, force=False, channel=1, timeout=None)

        self.stage.move_to(0, 1, scale=False)
        self.stage.move_to(0, 2, scale=False)
        self.stage.move_to(0, 4, scale=False)

        for z in range(50):
            self.stage.jog(direction=dir, channel=1, kind="builtin")
            time.sleep(0.4)
            self.stage.jog(direction=dir, channel=2, kind="builtin")
            time.sleep(0.4)
            self.stage.jog(direction=dir, channel=4, kind="builtin")
            time.sleep(0.4)

        #self.stage.home()  # Not working
        self.stage.close()
        pass

if __name__ == "__main__":

    mpc = MPC320Control()
    mpc.test_move()
    pass