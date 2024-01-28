from services.resonance_fit import RedPitayaResonanceFit, ResonanceFitGraphics, ResonanceFit
from functions.HMP4040Control import HMP4040Visa
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Slider
from typing import Union


class CavityLock(RedPitayaResonanceFit):
    def __init__(self):
        self.HMP4040 = HMP4040Visa()
        self.graphics = CavityLockGui(self)
        super().__init__()

    def update_tunings(self, index, value):
        pass

    def update_halogen_voltage(self, voltage):
        pass

    def update_laser_voltage(self, voltage):
        pass


ResonanceFitType = Union[CavityLock, ResonanceFit]


class CavityLockGui(ResonanceFitGraphics):
    def __init__(self, resonance_fit: ResonanceFitType):
        super().__init__(resonance_fit, show_buttons=True)

    def update_active_button(self, button_name):
        super().update_active_button(button_name)
        if button_name == "lock_button":
            pass

    def validate_input(self, text):
        pass

    def buttons_axis(self, size=(2, 4)):
        super().buttons_axis(size=size)

        laser_voltage_slider = Slider(self.buttons_subfigure.axes[2], 'Laser voltage', 0.0, 10.0, valinit=0.0)
        self.buttons.update({"laser_voltage_slider": laser_voltage_slider})
        laser_voltage_slider.on_changed(lambda val: self.resonance_fit.update_tunings(0, val))

        halogen_voltage_slider = Slider(self.buttons_subfigure.axes[3], 'Halogen voltage', 0.0, 10.0, valinit=0.0)
        self.buttons.update({"halogen_voltage_slider": halogen_voltage_slider})
        halogen_voltage_slider.on_changed(lambda val: self.resonance_fit.update_tunings(0, val))

        kp_slider = Slider(self.buttons_subfigure.axes[4], 'Kp', 0.0, 10.0, valinit=self.resonance_fit.tunings[0])
        self.buttons.update({"kp_slider": kp_slider})
        kp_slider.on_changed(lambda val: self.resonance_fit.update_tunings(0, val))

        ki_slider = Slider(self.buttons_subfigure.axes[5], 'Ki', 0.0, 10.0, valinit=self.resonance_fit.tunings[1])
        self.buttons.update({"ki_slider": ki_slider})
        ki_slider.on_changed(lambda val: self.resonance_fit.update_tunings(1, val))

        kd_slider = Slider(self.buttons_subfigure.axes[6], 'Kd', 0.0, 10.0, valinit=self.resonance_fit.tunings[2])
        self.buttons.update({"kd_slider": kd_slider})
        kd_slider.on_changed(lambda val: self.resonance_fit.update_tunings(2, val))

        lock_button = plt.Button(self.buttons_subfigure.axes[7], 'start lock')
        self.buttons.update({"lock_button": lock_button})
        lock_button.on_clicked(lambda _: self.update_active_button("choose_line_button"))
