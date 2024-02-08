from services.resonance_fit import ResonanceFit, ScopeDataLoader, CavityFwhm, DataLoaderRedPitaya, CavityKex
from services.new_cavity_lock.controller import CavityLockController
from services.new_cavity_lock.model import CavityLockModel

"""
This is the main file of the cavity lock service. The service is built on Model-View-Controller (MVC) architecture.
The Model is responsible for the data and the logic of the service. The View is responsible for the GUI of the service.
And the Controller is responsible for the communication between the Model and the View. That way, the Model and the View
are independent of each other and can be changed without affecting the other.
"""


if __name__ == '__main__':
    cavity = CavityKex(k_i=3.6, h=0.6)
    resonance_fit = ResonanceFit(cavity)
    data_loader = ScopeDataLoader(channels_dict={"transmission": 1, "rubidium": 3}, scope_ip=None)
    # data_loader = DataLoaderRedPitaya(host="rp-ffffb4.local")

    model = CavityLockModel(data_loader, resonance_fit, save=False, use_socket=True)

    controller = CavityLockController(model)
    controller.start()