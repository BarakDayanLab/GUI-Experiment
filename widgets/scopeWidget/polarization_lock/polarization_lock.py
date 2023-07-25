import time

from functions.PAX1000.PAXControl import PAXControl
from functions.MPC320.MPC320Control import MPC320Control


class PolarizationLockTest:

    def __init__(self):

        # Attempt to connect to the Polarimeter and Polarization Control
        try:
            #self.polarimeter = PAXControl()
            self.mickey_mouse = MPC320Control('38133894')
        except Exception as err:
            print('Failed to connect: %s' % err)
        pass

    def mainloop(self):
        while True:
            error = self.getError()
            time.sleep(2000)
            break

        return

    def getError(self):
        return 4


if __name__ == "__main__":

    pl = PolarizationLockTest()
    pl.mainloop()
