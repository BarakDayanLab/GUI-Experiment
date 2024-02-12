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
    controller = CavityLockController(save=False, use_socket=True)
    controller.start()
