from services.resonance_fit.data_loader import ScopeDataLoader, DataLoaderRedPitaya
from services.resonance_fit.cavity import CavityFwhm
from services.resonance_fit.view import App

if __name__ == '__main__':
    # data_loader = ScopeDataLoader(channels_dict={"transmission": 1, "rubidium": 3}, scope_ip=None)
    data_loader = DataLoaderRedPitaya()
    cavity = CavityFwhm()
    app = App(cavity, data_loader)
    app.mainloop()

