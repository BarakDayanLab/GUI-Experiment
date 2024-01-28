from services.resonance_fit.resonance_fit import ResonanceFit
from functions.RedPitayaWebsocket import Redpitaya
import numpy as np
import time
from services.resonance_fit.resonance_fit import ResonanceFitGraphics


class RedPitayaResonanceFit(ResonanceFit):
    def __init__(self, host="rp-ffffb4.local", graphics=None):
        super().__init__()
        self.config = {'locker': 'cavity'}
        self.red_pitaya = Redpitaya(host,
                                    got_data_callback=self.got_data_callback,
                                    dialogue_print_callback=self.dialogue_print_callback,
                                    config=self.config)
        self.red_pitaya.run()
        self.graphics = graphics(self) if graphics is not None else None

        while True:
            time.sleep(1)

    def got_data_callback(self, data, parameters):
        if self.pause:
            return

        transmission_spectrum, rubidium_lines = np.array(data)
        if transmission_spectrum is None or rubidium_lines is None:
            return

        self.update_transmission_spectrum(transmission_spectrum)
        self.update_rubidium_lines(rubidium_lines)

        if hasattr(self, "graphics"):
            self.graphics.plot_data()

        if not self.calibrate_x_axis():
            return
        if not self.fit_transmission_spectrum():
            return

        params = self.cavity.get_fit_parameters() + [self.lock_error]
        self.fit_params_history = np.vstack([self.fit_params_history, params])

        if hasattr(self, "graphics"):
            self.graphics.plot_fit()
            self.graphics.activate_button()

    @staticmethod
    def dialogue_print_callback(text, color=""):
        print(text)


if __name__ == '__main__':
    RedPitayaResonanceFit()
