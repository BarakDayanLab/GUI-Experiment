import time
from functions.AGUC2 import controller
from pynput.keyboard import Key, Listener, Controller
from pynput import keyboard

import numpy as np
import matplotlib.pyplot as plt

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


class MyTestClass:

    def __init__(self):
        pass

    def test_something(self):

        # a little hack to get screen size; from here [1]
        mgr = plt.get_current_fig_manager()
        mgr.full_screen_toggle()
        py = mgr.canvas.height()
        px = mgr.canvas.width()
        mgr.window.close()
        # hack end

        px = 0

        figManager = plt.get_current_fig_manager()
        # if px=0, plot will display on 1st screen
        figManager.window.move(px, 0)
        figManager.window.showMaximized()
        figManager.window.setFocus()

        plt.figure()
        # Data for plotting
        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)

        fig, ax = plt.subplots()
        ax.plot(t, s)

        ax.set(xlabel='time (s)', ylabel='voltage (mV)',
               title='About as simple as it gets, folks')
        ax.grid()

        # fig.savefig("test.png")
        plt.show(block=False)

        plt.pause(0.01)
        time.sleep(20)
        plt.close()
        pass


if __name__ == "__main__":
    cl = aguc2_test()
    cl.test_it()

    # cl = MyTestClass()
    # cl.test_something()
