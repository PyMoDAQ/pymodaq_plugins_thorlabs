"""
PyMoDAQ plugin for thorlabs instruments based on the TLPM library allowing
remote control and monitoring of up to eight power and energy meters.
This software is compatible with our Power Meter Consoles and Interfaces (PM100A and PM101 Series),
Power and Energy Meter Consoles and Interfaces (PM100D, PM400, PM100USB, PM103 Series, and legacy PM200),
Position & Power Meter Interfaces (PM102 Series),
Wireless Power Meters (PM160, PM160T, and PM160T-HP),
and USB-Interface Power Meters (PM16 Series)

you have to install the Optical Monitor Software from Thorlabs to obtain the library

The installation should create (following the manual) an environment variable called either VXIPNPPATH64 or
VXIPNPPATH depending on your platform (32 or 64 bits) pointing to where the TLPM library is
(usually C:\Program Files\IVI Foundation\VISA)

This plugin is using the Instrumental_lib package directly interfacing the C library with the nice **instrument** wrapper
"""
import sys
from qtpy.QtCore import QThread
from easydict import EasyDict as edict
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo, DataFromPlugins
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base, main
from collections import OrderedDict
import numpy as np
from pymodaq.daq_viewer.utility_classes import comon_parameters

from instrumental import list_instruments, instrument

psets = list_instruments(module='powermeters.thorlabs_tlpm')

DEVICES = [f"{pset['model']}/{pset['serial']}" for pset in psets]


class DAQ_0DViewer_TLPMPowermeterInst(DAQ_Viewer_base):

    _controller_units = 'W'

    params = comon_parameters + [
        {'title': 'Devices:', 'name': 'devices', 'type': 'list', 'limits': DEVICES},
        {'title': 'Info:', 'name': 'info', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Wavelength:', 'name': 'wavelength', 'type': 'float', 'value': 532., 'suffix': 'nm'},
        ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)


    def ini_detector(self, controller=None):
        """
            Initialisation procedure of the detector.

            Returns
            -------

                The initialized status.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False, info="", x_axis=None, y_axis=None, controller=None))
        try:

            if self.settings.child(('controller_status')).value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller = controller
            else:

                self.controller = instrument(psets[DEVICES.index(self.settings['devices'])])
                self.controller.power_unit = self._controller_units
                info = self.controller.get_device_info()

                self.settings.child('info').setValue(str(info))

            self.settings.child('wavelength').setOpts(
                limits=[wrange.magnitude for wrange in self.controller.get_wavelength_range()])
            self.settings.child('wavelength').setValue(self.controller.wavelength.magnitude)

            self.status.initialized = True
            self.status.controller = self.controller
            self.status.info = str(info)
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status


    def commit_settings(self, param):
        """
        """
        if param.name() == 'wavelength':
            self.controller.wavelength = self.settings.child('wavelength').value()
            self.settings.child('wavelength').setValue(self.controller.wavelength)

    def close(self):
        """
            close the current instance of Keithley viewer.
        """
        self.controller.close()

    def grab_data(self, Naverage=1, **kwargs):
        """
            | Start new acquisition.
            | grab the current values with keithley profile procedure.
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================
        """
        data = np.array([np.mean([self.controller.get_power().magnitude for ind in range(Naverage)])])
        self.data_grabed_signal.emit([DataFromPlugins(name='Powermeter', data=[data],
                                                      dim='Data0D', labels=['Power (W)'],)])


    def stop(self):
        """
        """
        return ""


if __name__ == '__main__':
    main(__file__)
