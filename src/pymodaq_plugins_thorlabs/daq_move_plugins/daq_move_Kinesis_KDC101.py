from pymodaq.daq_move.utility_classes import DAQ_Move_base, main
from pymodaq.daq_move.utility_classes import comon_parameters
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo
import clr
import sys
from easydict import EasyDict as edict


class DAQ_Move_Kinesis_KDC101(DAQ_Move_base):
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

    _controller_units = 'mm'

    kinesis_path = 'C:\\Program Files\\Thorlabs\\Kinesis'
    try:
        from System import Decimal
        from System import Action
        from System import UInt64
        
        sys.path.append(kinesis_path)
        
        clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
        clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
        clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
        
        import Thorlabs.MotionControl.KCube.DCServoCLI as Integrated
        import Thorlabs.MotionControl.DeviceManagerCLI as Device
        import Thorlabs.MotionControl.GenericMotorCLI as Generic
        
        Device.DeviceManagerCLI.BuildDeviceList()
        
        serialnumbers = [str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(Integrated.KCubeDCServo.DevicePrefix)]
    

    except:
        serialnumbers = []
    is_multiaxes = False

    stage_names = []

    params = [{'title': 'Kinesis library:', 'name': 'kinesis_lib', 'type': 'browsepath', 'value': kinesis_path},
              {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
              {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serialnumbers},
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group', 'visible': is_multiaxes, 'children': [
                  {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes,
                   'default': False},
                  {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master',
                   'limits': ['Master', 'Slave']},
                  {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'limits': stage_names},

              ]}] + comon_parameters



    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
                 
        self.controller = None
        self.settings.child('epsilon').setValue(0)

        try:
            # kinesis_path=os.environ['Kinesis'] #environement variable pointing to 'C:\\Program Files\\Thorlabs\\Kinesis'
            # to be adjusted on the different computers

            self.move_done_action = self.Action[self.UInt64](self.move_done_here)

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [getLineInfo() + str(e), 'log']))
            raise Exception(getLineInfo() + str(e))


    def move_done_here(self, pos_action):
        print(f'posaction is {pos_action}')
        position = self.check_position()
        self.move_done(position)

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
                sys.path.append(param.value())
                clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
                clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
                clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
                import Thorlabs.MotionControl.KCube.DCServoCLI as Integrated
                import Thorlabs.MotionControl.DeviceManagerCLI as Device
                import Thorlabs.MotionControl.GenericMotorCLI as Generic
                Device.DeviceManagerCLI.BuildDeviceList()
                serialnumbers = [str(ser) for ser in
                                 Device.DeviceManagerCLI.GetDeviceList(Integrated.KCubeDCServo.DevicePrefix)]

            except:
                serialnumbers = []
            self.settings.child('serial_number').setOpts(limits=serialnumbers)

    def ini_stage(self, controller=None):
        
        """
            Initialize the controller and stages (axes) with given parameters.

            =============== ================================================ =========================================================================================
            **Parameters**   **Type**                                         **Description**
            *controller*     instance of the specific controller object       If defined this hardware will use it and will not initialize its own controller instance
            *stage*          instance of the stage (axis or whatever) object  ???
            =============== ================================================ =========================================================================================

            Returns
            -------
            Easydict
                dictionnary containing keys:
                 * *info* : string displaying various info
                 * *controller*: instance of the controller object in order to control other axes without the need to init the same controller twice
                 * *stage*: instance of the stage (axis or whatever) object
                 * *initialized*: boolean indicating if initialization has been done corretly

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            self.status.update(edict(info="", controller=None, initialized=False))

            # check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)

            # if mutliaxes then init the controller here if Master state otherwise use external controller
            
            if self.settings.child('multiaxes', 'ismultiaxes').value() and self.settings.child('multiaxes',
                                                                                               'multi_status').value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller = controller
            else:  # Master stage

                self.Device.DeviceManagerCLI.BuildDeviceList()
                serialnumbers = self.Device.DeviceManagerCLI.GetDeviceList(self.Integrated.KCubeDCServo.DevicePrefix)
                ser_bool = self.settings.child('serial_number').value() in serialnumbers
                if ser_bool:
                    self.controller = self.Integrated.KCubeDCServo.CreateKCubeDCServo(
                        self.settings.child('serial_number').value())
                    self.controller.Connect(self.settings.child('serial_number').value())
                    self.controller.WaitForSettingsInitialized(5000)
                    self.controller.StartPolling(250)
                else:
                    raise Exception("Not valid serial number")

            info = self.controller.GetDeviceInfo().Name
            self.settings.child('controller_id').setValue(info)
            if not (self.controller.IsSettingsInitialized()):
                raise (Exception("no Stage Connected"))
            self.motorSettings = self.controller.GetMotorConfiguration(self.settings.child('serial_number').value(), 2)
            self.controller.SetBacklash(self.Decimal(0))
            self.status.info = info
            self.status.controller = self.controller
            self.status.initialized = True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def close(self):
        """
            close the current instance of Kinesis instrument.
        """
        self.controller.StopPolling();
        self.controller.Disconnect();
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

    def check_position(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos = self.Decimal.ToDouble(self.controller.Position)
        pos = self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('check_position', [pos]))
        return pos

    def move_Abs(self, position):
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
        self.controller.MoveTo(self.Decimal(position), self.move_done_action)


    def move_Rel(self, position):
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

        position = self.set_position_relative_with_scaling(position)

        self.controller.MoveRelative(self.Generic.MotorDirection.Forward, self.Decimal(position), self.move_done_action)



    def move_Home(self):
        """
            Make the absolute move to original position (0).
        """
        self.controller.Home(self.move_done_action)


if __name__ == '__main__':
    main(__file__)