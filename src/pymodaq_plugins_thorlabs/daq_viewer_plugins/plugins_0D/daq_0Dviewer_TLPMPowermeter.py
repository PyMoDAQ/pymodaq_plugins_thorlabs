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

This plugin is making use of the TLPM.py script provided by thorlabs. An alternative is to use the TLPMPowermeterInst
plugin using the Instrumental_lib package directly interfacing the C library with the nice Instrument wrapper
"""
from easydict import EasyDict as edict
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, main

import numpy as np
from pymodaq.control_modules.viewer_utility_classes import comon_parameters
from pymodaq_plugins_thorlabs.hardware.powermeter import CustomTLPM, DEVICE_NAMES


class DAQ_0DViewer_TLPMPowermeter(DAQ_Viewer_base):

    _controller_units = 'W'
    devices = DEVICE_NAMES

    params = comon_parameters + [
        {'title': 'Devices:', 'name': 'devices', 'type': 'list', 'limits': devices},
        {'title': 'Info:', 'name': 'info', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Wavelength:', 'name': 'wavelength', 'type': 'float', 'value': 532.,},
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
                index = DEVICE_NAMES.index(self.settings['devices'])
                self.controller = CustomTLPM()
                info = self.controller.infos.get_devices_info(index)
                self.controller.open_by_index(index)
                self.settings.child('info').setValue(str(info))

            self.settings.child('wavelength').setOpts(limits=self.controller.wavelength_range)
            self.controller.wavelength = self.settings.child('wavelength').value()
            self.settings.child('wavelength').setValue(self.controller.wavelength)

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
        data = [np.array([self.controller.get_power()])]
        self.data_grabed_signal.emit([DataFromPlugins(name='Powermeter', data=data,
                                                      dim='Data0D', labels=['Power (W)'],)])


    def stop(self):
        """
        """
        return ""


if __name__ == '__main__':
    main(__file__)
