import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
from pymodaq_plugins_thorlabs.hardware.ccsxxx import CCSXXX

class DAQ_1DViewer_CCSXXX(DAQ_Viewer_base):
    """ Instrument plugin class for a 1D viewer.

    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """
    params = comon_parameters + [
        {'title': 'Integration time', 'name': 'integration_time', 'type': 'float', 'value': 100.0e-3}, # in seconds
        {'title': 'Resource name', 'name': 'resource_name', 'type': 'str', 'value': 'USB0::0x1313::0x8087::M00934802::RAW'},
    ]

    def ini_attributes(self):
        """Initialize attributes for the DAQ_1DViewer_CCSXXX class."""
        self.controller: CCSXXX = None
        self.x_axis = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == "integration_time":
            self.controller.set_integration_time(self.settings['integration_time'])

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        self.ini_detector_init(slave_controller=controller)

        if self.is_master:
            self.controller = CCSXXX(self.settings['resource_name'])
            self.controller.connect()

        data_x_axis = self.controller.get_wavelength_data()
        self.x_axis = Axis(data=data_x_axis, label='Wavelength', units='nm', index=0)

        self.dte_signal_temp.emit(DataToExport(name='CCSXXX',
                                               data=[DataFromPlugins(name='Spectrum',
                                                                     data=[np.zeros(len(data_x_axis)),],
                                                                     dim='Data1D', labels=['Intensity'],
                                                                     axes=[self.x_axis])]))

        info = "CCSXXX spectrometer initialized"
        initialized = True
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        self.controller.close()

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        self.controller.start_scan()
        data_tot = self.controller.get_scan_data()
        self.dte_signal.emit(DataToExport('CCSXXX',
                                          data=[DataFromPlugins(name='Spectrum', data=[data_tot],
                                                                dim='Data1D', labels=['Intensity'],
                                                                axes=[self.x_axis])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        # raise NotImplemented  # when writing your own plugin remove this line
        return ''

if __name__ == '__main__':
    main(__file__)
