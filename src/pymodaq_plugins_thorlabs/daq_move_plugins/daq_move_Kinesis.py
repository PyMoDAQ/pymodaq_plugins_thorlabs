from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main
from pymodaq.control_modules.move_utility_classes import comon_parameters_fun
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.logger import set_logger, get_module_name
import clr
from qtpy import QtWidgets
import sys
from easydict import EasyDict as edict

from System import Decimal
from System import Action
from System import UInt64

kinesis_path = 'C:\\Program Files\\Thorlabs\\Kinesis'
sys.path.append(kinesis_path)
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
import Thorlabs.MotionControl.IntegratedStepperMotorsCLI as Integrated
import Thorlabs.MotionControl.DeviceManagerCLI as Device
import Thorlabs.MotionControl.GenericMotorCLI as Generic

MOVEDONEACTION = False
logger = set_logger(get_module_name(__file__))


class DAQ_Move_Kinesis(DAQ_Move_base):
    """
        Wrapper object to access the kinesis fonctionnalities, similar wrapper for all controllers.

        =============== ==================
        **Attributes**   **Type**
        *kinesis_path*   string
        *serialnumbers*  int list
        *params*         dictionnary list
        =============== ==================

        See Also
        --------
        daq_utils.ThreadCommand

    """
    _controller_units = 'degrees'
    _epsilon = 0.05

    try:

        Device.DeviceManagerCLI.BuildDeviceList()
        serialnumbers = [str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)]

    except:
        serialnumbers = []
    is_multiaxes = False

    stage_names = []

    params = [{'title': 'Kinesis library:', 'name': 'kinesis_lib', 'type': 'browsepath', 'value': kinesis_path},
              {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
              {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serialnumbers},
              ] + comon_parameters_fun(is_multiaxes, epsilon=_epsilon)


    def ini_attributes(self):

        self.controller: Integrated.CageRotator.CreateCageRotator = None

        try:
            if MOVEDONEACTION:
                self.move_done_action = Action[UInt64](self.someaction)  # if selected wil trigger
                # self.someaction when move is done

            else:
                self.move_done_action = 0  # if selected will return immediately


        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [getLineInfo() + str(e), 'log']))
            raise Exception(getLineInfo() + str(e))

    def someaction(self, pos_action):
        position = self.get_actuator_value()
        logger.debug(f'posaction is {pos_action} and position is {position}')

    def commit_settings(self, param):
        """
            | Activate any parameter changes on the hardware.
            | Called after a param_tree_changed signal received from DAQ_Move_main.

            =============== ================================ ========================
            **Parameters**  **Type**                          **Description**
            *param*         instance of pyqtgraph parameter  The parameter to update
            =============== ================================ ========================
        """
        if param.name() == 'kinesis_lib':
            try:
                Device.DeviceManagerCLI.BuildDeviceList()
                serialnumbers = [str(ser) for ser in
                                 Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)]

            except:
                serialnumbers = []
            self.settings.child('serial_number').setOpts(limits=serialnumbers)

    def ini_stage(self, controller=None):
        """
        """

        Device.DeviceManagerCLI.BuildDeviceList()
        serialnumbers = Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)
        ser_bool = self.settings['serial_number'] in serialnumbers
        if ser_bool:
            self.controller = self.ini_stage_init(controller,
                                                  Integrated.CageRotator.CreateCageRotator(
                                                      self.settings['serial_number']))
        else:
            raise Exception("Not valid serial number")

        if self.settings['multiaxes', 'multi_status'] == "Master":

            self.controller.Connect(self.settings['serial_number'])
            self.controller.WaitForSettingsInitialized(5000)
            self.controller.StartPolling(250)

        info = self.controller.GetDeviceInfo().Name
        self.settings.child('controller_id').setValue(info)
        if not (self.controller.IsSettingsInitialized()):
            raise (Exception("no Stage Connected"))
        else:
            self.controller.LoadMotorConfiguration(self.settings['serial_number'])
        self.controller.SetBacklash(Decimal(0))

        initialized = True
        return info, initialized

    def close(self):
        """
            close the current instance of Kinesis instrument.
        """
        self.controller.StopPolling()
        self.controller.Disconnect()
        self.controller.Dispose()
        self.controller = None

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        self.controller.stop(0)
        self.move_done()

    def get_actuator_value(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """

        pos = Decimal.ToDouble(self.controller.ContinuousRotationPosition)
        logger.debug(f'Motor state is {self.controller.State} and position is {pos}')
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position):
        """
            Make the hardware absolute move from the given position of the Kinesis instrument after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling

        """
        position = self.check_bound(position)
        self.target_position = position

        position = self.set_position_with_scaling(position)
        logger.debug(f'Should move to {position} but decimal gets {Decimal.ToDouble(Decimal(position))}')
        self.controller.MoveTo(Decimal(position), self.move_done_action)
        QtWidgets.QApplication.processEvents()

    def move_rel(self, position):
        """
            | Make the hardware relative move from the given position of the Kinesis instrument after thread command signal was received in DAQ_Move_main.
            |
            | The final target position is given by **current_position+position**.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling

        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position
        logger.debug(f'Should move to {Decimal.ToDouble(Decimal(self.target_position))}')
        position = self.set_position_relative_with_scaling(position)

        self.controller.MoveRelative(Generic.MotorDirection.Forward, Decimal(position), self.move_done_action)

    def move_home(self):
        """
            Make the absolute move to original position (0).
        """
        self.controller.Home(self.move_done_action)


if __name__ == '__main__':
    main(__file__, init=False)
