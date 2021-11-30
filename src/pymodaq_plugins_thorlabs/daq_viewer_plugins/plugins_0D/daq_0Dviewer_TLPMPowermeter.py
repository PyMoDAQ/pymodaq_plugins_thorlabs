import sys
from qtpy.QtCore import QThread
from easydict import EasyDict as edict
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo, DataFromPlugins
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base, main
from collections import OrderedDict
import numpy as np
from pymodaq.daq_viewer.utility_classes import comon_parameters
from pymodaq_plugins_thorlabs.hardware.powermeter import SimpleTLPM, DEVICE_NAMES


class DAQ_0DViewer_TLPMPowermeter(DAQ_Viewer_base):

    _controller_units = 'W'
    devices = DEVICE_NAMES

    params = comon_parameters+[
            {'title': 'Devices:', 'name': 'devices', 'type': 'list', 'limits': devices},
             {'title': 'Info:', 'name': 'info', 'type': 'str', 'value': '', 'readonly': True},
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
                self.controller = SimpleTLPM()
                info = self.controller.infos.get_devices_info(index)
                self.controller.open_by_index(index)
                self.settings.child('info').setValue(str(info))

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
        pass

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
        self.data_grabed_signal.emit([DataFromPlugins(name='KPA101 Positions', data=data,
                                                      dim='Data0D', labels=['Power (W)'],)])


    def stop(self):
        """
        """
        return ""


if __name__ == '__main__':
    main(__file__)
