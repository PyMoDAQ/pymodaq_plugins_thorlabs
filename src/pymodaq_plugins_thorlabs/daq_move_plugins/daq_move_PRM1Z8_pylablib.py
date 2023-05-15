from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main
from pymodaq.control_modules.move_utility_classes import comon_parameters_fun
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from easydict import EasyDict as edict

import pylablib.devices.Thorlabs as Thorlabs



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
    stage_names = []
    _epsilon = 0.1
    _dvc = Thorlabs.list_kinesis_devices()
    #serialnumbers = [d[0] for d in _dvc if d[1] == 'APT DC Motor Controller']
    serialnumbers = [d[0] for d in _dvc]

    params= [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serialnumbers},
             {'title': 'Home Position:', 'name': 'home_position', 'type': 'float', 'value': 0.0},
             {'title': 'Set Zero', 'name': 'set_zero', 'type': 'bool_push', 'value': False},
             {'title': 'Reset Home', 'name': 'reset_home', 'type': 'bool_push', 'value': False},

             ] + comon_parameters_fun(is_multiaxes, stage_names, epsilon=_epsilon)

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.settings.child('epsilon').setValue(0.005)
        self.settings.child('epsilon').setReadonly()

        self.settings.child('timeout').setValue(100)

        #Scaling and bounds can be set to False because they are just not needed
        self.settings.child('bounds', 'is_bounds').setValue(False)
        self.settings.child('bounds', 'is_bounds').setReadonly()
        self.settings.child('bounds').hide()
        self.settings.child('scaling', 'use_scaling').setValue(False)
        self.settings.child('scaling', 'use_scaling').setReadonly()
        self.settings.child('scaling').hide()

        #Home is fixed (for now)
        # self.settings.child('home_position').setReadonly()

        # self.settings.child('scaling','scaling').setReadonly()
        # self.settings.child('scaling','offset').setReadonly()

    def commit_settings(self,param):
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
                self.check_position()
                self.settings.child('set_zero').setValue(False)
        elif param.name() == 'reset_home':
            if param.value() == True:
                self.controller.home(force=True, timeout=self.settings.child('timeout').value())
                self.check_position()
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
        try:
            self.status.update(edict(info="",controller=None,initialized=False))

            #check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)

            # if multiaxes then init the controller here if Master state otherwise use external controller
            if self.settings.child('multiaxes','ismultiaxes').value() and self.settings.child('multiaxes','multi_status').value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller = controller
            else: #Master stage
                try:
                    controller = Thorlabs.kinesis.KinesisMotor(self.settings.child('serial_number').value(),scale='stage')
                except:
                    raise Exception(f'No controller found with serial number {self.settings.child("serial_number").value()}')
                else:
                    self.controller = controller

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

            #IDK what that does but ok
            self.status.info = info.notes
            self.status.controller = self.controller
            self.status.initialized = True
            return self.status
        #This is in case something fails
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[getLineInfo()+ str(e),'log']))
            self.status.info=getLineInfo()+ str(e)
            self.status.initialized=False
            return self.status

    def close(self):
        """
            close the current instance of Kinesis Flipper instrument.
        """
        self.controller.close()
        self.controller = None

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        # self.controller.stop(0)
        self.move_done()

    def check_position(self):
        """
            Get the current hardware position with scaling conversion of the Kinesis
            instrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        #Get position = 0 or 1, possibly None if unknown
        pos = self.controller.get_position()
        #Repoll if pos returns none
        while pos == None:
            pos = self.controller.get_position()

        #This is superfluous as there is not scaling
        # pos = self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('check_position', [pos]))
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

        self.controller.move_to(position)
        self.emit_status(ThreadCommand('Update_Status', [f'Moving to position: {position}']))

        self.target_position = position
        self.poll_moving()

    def move_rel(self,position):
        """ Move the actuator to the relative target actuator value defined by position
        Parameters
        ----------
        position: (float) value of the relative target positioning
        """
        self.current_position = self.check_position()
        # rel_move  = self.check_bound(self.current_position+position)-self.current_position
        new_pos = self.check_bound(self.current_position + position)
        self.target_position = new_pos

        # self.target_position = position
        self.controller.move_to(new_pos)
        self.emit_status(ThreadCommand('Update_Status', [f'Moving to position: {position}']))
        self.poll_moving()

    def move_home(self):
        """
            Make the absolute move to original position (0).
        """
        home = self.settings.child('home_position').value()
        self.target_position = home
        self.controller.move_to(home)
        self.emit_status(ThreadCommand('Update_Status', [f'Moving home: {home}']))
        self.poll_moving()


if __name__ == '__main__':
    main(__file__, init=False)