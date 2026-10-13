import sys
from qtpy.QtCore import QThread

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter

from easydict import EasyDict as edict
from pymodaq.utils.daq_utils import getLineInfo
from pymodaq.utils.data import DataFromPlugins
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from collections import OrderedDict
import numpy as np
import clr
from pymodaq.control_modules.viewer_utility_classes import comon_parameters




class DAQ_0DViewer_Kinesis_KPA101(DAQ_Viewer_base):
    """ Plugin controlling the KPA101 Positionaligner detector

    """
    ##checking VISA resources
    supported_platforms = ('win32',)  # a Windows driver

    _controller_units = 'V'

    try:
        kinesis_path = 'C:\\Program Files\\Thorlabs\\Kinesis'
        sys.path.append(kinesis_path)
        clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
        clr.AddReference("Thorlabs.MotionControl.KCube.PositionAlignerCLI")
        import Thorlabs.MotionControl.DeviceManagerCLI as Device
        import Thorlabs.MotionControl.KCube.PositionAlignerCLI as PosAligner
        Device.DeviceManagerCLI.BuildDeviceList()
        # %%
        serialnumbers = [str(ser) for ser in
                         Device.DeviceManagerCLI.GetDeviceList(PosAligner.KCubePositionAligner.DevicePrefix)]
        # %%

    except:
        serialnumbers=[]

    params = comon_parameters+[
            {'title': 'Kinesis library:', 'name': 'kinesis_lib', 'type': 'browsepath', 'value': kinesis_path},
            {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serialnumbers},
            {'title': 'Device:', 'name': 'device_name', 'type': 'str', 'value': ''},
            {'title': 'Polling time (ms):', 'name': 'polling_time', 'type': 'int', 'value': 250},
            ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.controller = None

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

        if not self.is_master:
            self.controller = controller
        else:
            self.Device.DeviceManagerCLI.BuildDeviceList()
            serialnumbers = self.Device.DeviceManagerCLI.GetDeviceList(self.PosAligner.KCubePositionAligner.DevicePrefix)
            ser_bool = self.settings['serial_number'] in serialnumbers
            if ser_bool:
                self.controller = self.PosAligner.KCubePositionAligner.CreateKCubePositionAligner(
                    self.settings['serial_number'])
                self.controller.Connect(self.settings['serial_number'])
                if not self.controller.IsSettingsInitialized():
                    self.controller.WaitForSettingsInitialized(5000)
                self.controller.StartPolling(self.settings['polling_time'])
                self.emit_status(ThreadCommand('update_main_settings', [['wait_time'],
                                                        self.settings['polling_time'], 'value']))
                QThread.msleep(500)
                self.controller.EnableDevice()
                QThread.msleep(500)
                deviceInfo = self.controller.GetDeviceInfo()
                self.settings['device_name'] = deviceInfo.Name


        initialized = True
        info = 'Device initialized'
        return info, initialized


    def commit_settings(self, param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================= ============================
            **Parameters**   **Type**                         **Description**
            *param*         instance of pyqtgraph.parameter   The parameter to be checked.
            =============== ================================= ============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            if param.name() == 'kinesis_lib':
                try:
                    sys.path.append(param.value())
                    clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
                    clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
                    clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
                    import Thorlabs.MotionControl.IntegratedStepperMotorsCLI as Integrated
                    import Thorlabs.MotionControl.DeviceManagerCLI as Device
                    import Thorlabs.MotionControl.GenericMotorCLI as Generic
                    Device.DeviceManagerCLI.BuildDeviceList()
                    serialnumbers = [str(ser) for ser in
                                     Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)]

                except:
                    serialnumbers = []
                self.settings.child(('serial_number')).setOpts(limits=serialnumbers)

            elif param.name() == 'polling_time':
                self.controller.StopPolling()
                QThread.msleep(500)
                self.controller.StartPolling(self.settings.child(('polling_time')).value())
                QThread.msleep(500)
                self.emit_status(ThreadCommand('update_main_settings', [['wait_time'], param.value(), 'value']))


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))

    def close(self):
        """
            close the current instance of Keithley viewer.
        """
        if self.controller is not None:
            self.controller.DisableDevice()
            self.controller.StopPolling()
            self.controller.Disconnect(False)

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
        status = self.controller.Status
        data = [np.array([status.PositionDifference.X]), np.array([status.PositionDifference.Y])]
        data_intens = [np.array([status.Sum])]
        self.data_grabed_signal.emit([DataFromPlugins(name='KPA101 Positions', data=data, dim='Data0D',
                                                      labels=['X (V)', 'Y (V)'],),
                                      DataFromPlugins(name='KPA101 Intensity', data=data_intens, dim='Data0D',
                                                      labels=['Intensity'],)])


    def stop(self):
        """
            not implemented?
        """
        return ""


if __name__ == '__main__':
    main(__file__, init=False)