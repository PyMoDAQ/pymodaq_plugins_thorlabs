from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main
from pymodaq.control_modules.move_utility_classes import comon_parameters_fun
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from easydict import EasyDict as edict

import pylablib.devices.Thorlabs as Thorlabs

from pymodaq_plugins_thorlabs.utils import Config as PluginConfig

config = PluginConfig()


class DAQ_Move_PRM1Z8_pylablib(DAQ_Move_base):
    """
        Wrapper object to access the Flipper functionalities, similar wrapper for all controllers.
        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """
    _controller_units = 'deg'
    is_multiaxes = False
    _stage_names = []
    _epsilon = 0.005
    _dvc = Thorlabs.list_kinesis_devices()
    #serialnumbers = [d[0] for d in _dvc if d[1] == 'APT DC Motor Controller']
    serialnumbers = [d[0] for d in _dvc]

    params= [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serialnumbers},
             {'title': 'Home Position:', 'name': 'home_position', 'type': 'float', 'value': 0.0},
             {'title': 'Set Zero', 'name': 'set_zero', 'type': 'bool_push', 'value': False},
             {'title': 'Reset Home', 'name': 'reset_home', 'type': 'bool_push', 'value': False},

             ] + comon_parameters_fun(is_multiaxes, _stage_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.settings.child('epsilon').setReadonly()
        self.settings.child('timeout').setValue(100)

        self.settings.child('bounds').show(config('PRM1Z8', 'show_bounds'))
        self.settings.child('scaling').show(config('PRM1Z8', 'show_scaling'))

    def commit_settings(self, param):
        """
            | Activate any parameter changes on the hardware.
            | Called after a param_tree_changed signal received from DAQ_Move_main.

            =============== ================================ ========================
            **Parameters**  **Type**                          **Description**
            *param*         instance of pyqtgraph Parameter  The parameter to update
            =============== ================================ ========================
        """
        if param.name() == 'set_zero':
            if param.value() == True:
                self.controller.set_position_reference(scale=True)
                self.get_actuator_value()
                self.settings.child('set_zero').setValue(False)
        elif param.name() == 'reset_home':
            if param.value() == True:
                self.controller.home(force=True, timeout=self.settings['timeout'])
                self.get_actuator_value()
                self.settings.child('reset_home').setValue(False)

    def ini_stage(self,controller=None):
        """Initialize the controller and stages (axes) with given parameters.

            ============== =========================================== ===========================================================================================
            **Parameters**  **Type**                                     **Description**

            *controller*    instance of the specific controller object  If defined this hardware will use it and will not initialize its own controller instance
            ============== =========================================== ===========================================================================================

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
        self.ini_stage_init(controller, Thorlabs.kinesis.KinesisMotor(self.settings['serial_number'], scale='stage'))

        if not self.controller.is_opened():
            self.controller.open()

        #Getting the information from the device
        info = self.controller.get_device_info()

        #Setting the name of the controller
        #asserting that the controller is scale_aware and
        stage_name = self.controller.get_stage()
        assert stage_name == 'PRM1-Z8'
        self.settings.child('controller_id').setValue(stage_name)

        unit = self.controller.get_scale_units()
        assert unit == 'deg'
        initialized = True
        return info.notes, initialized

    def close(self):
        """
            close the current instance of Kinesis Flipper instrument.
        """
        if self.controller is not None:
            self.controller.close()

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        self.move_done()

    def get_actuator_value(self):
        """
            Get the current hardware position with scaling conversion of the Kinesis
            instrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos = self.controller.get_position()
        #Repoll if pos returns none
        while pos == None:
            pos = self.controller.get_position()
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self,position):
        """
            Make the hardware absolute move from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       int       either 1 or 2 for the flipper
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling

        """
        position = self.check_bound(position)
        self.target_position = position
        position = self.set_position_with_scaling(position)

        self.controller.move_to(position)
        self.emit_status(ThreadCommand('Update_Status', [f'Moving to position: {position}']))

    def move_rel(self,position):
        """ Move the actuator to the relative target actuator value defined by position
        Parameters
        ----------
        position: (float) value of the relative target positioning
        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position
        position = self.set_position_relative_with_scaling(position)

        self.controller.move_to(self.target_position)

    def move_home(self):
        """
            Make the absolute move to original position (0).
        """
        home = self.settings['home_position']
        self.target_position = home
        self.move_abs(home)


if __name__ == '__main__':
    main(__file__, init=False)