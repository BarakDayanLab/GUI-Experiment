import time
from functions.AGUC2 import controller
from pynput.keyboard import Key, Listener, Controller
from pynput import keyboard

#
# AGUC-2 is a Piezo Motor Motion Controller
# (do not confuse with AGUC-8 which controls 8 axis)
#

class aguc2_test:

    def __init__(self):
        self.c = controller.AGUC2("COM14",
                                  axis1alias='L1',
                                  axis2alias='L2',
                                  stepAmp1=35,
                                  stepAmp2=35)  # "\\Device\\000000af"
        if self.c.isDisconnected():
            print('Not connected! Try re-connecting!')
            for attempt in range(1,10):
                self.c.attemptReconnect()
                if self.c.isConnected():
                    break
                print('Not connected! Trying again...')
                time.sleep(1.5)

        pass

    def initiate_keyboard_controller(self):
        self.alt_modifier = False

        self.controller = Controller()
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()  # start to listen on a separate thread

        # Keyboard control - Collect events until released
        # self.controller = Controller()
        # with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
        #     # ... other code ...
        #     listener.join()

    def on_press(self, key):
        print(f'{key} pressed')
        if key == Key.alt_l:
            self.alt_modifier = True

    def on_release(self, key):
        print(f'{key} released')
        if key == Key.esc and self.alt_modifier:
            print('Alt-ESC released')

        if key == Key.alt_l:
            self.alt_modifier = False

    def test_it(self):
        ver = self.c.getVersion()

        self.c.setStepAmplitude(1, negative_amp=49, positive_amp=48)

        plate = 'L1'
        self.c.setZero(plate)
        for i in range(1, 4):
            self.c.move(plate, 200)
            print(i)
            time.sleep(1)
        self.c.goToZero(plate)

        self.c.close()
        pass

if __name__ == "__main__":
    cl = aguc2_test()
    cl.test_it()
