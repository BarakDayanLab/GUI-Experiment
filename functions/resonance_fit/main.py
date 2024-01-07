import cmd
from load_data import Scope


class FitResonance:
    def __init__(self):
        transmission_channel = input("Enter the transmission signal channel: ")
        reflection_channel = input("Enter the reflection signal channel: ")
        rubidium_channel = input("Enter the rubidium channel: ")
        channels = {"transmission": transmission_channel, "reflection": reflection_channel, "rubidium":rubidium_channel}
        data_loader = Scope(channels)

        input("Turn the ")

    def
