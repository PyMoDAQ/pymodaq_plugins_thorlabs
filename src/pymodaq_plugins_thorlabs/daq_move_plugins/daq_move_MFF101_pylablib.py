from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq.control_modules.move_utility_classes import comon_parameters
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo
from easydict import EasyDict as edict

import pylablib.devices.Thorlabs as Thorlabs

is_multiaxes = False
stage_names = []

class DAQ_Move_MFF101_pylablib(DAQ_Move_base):
    """
        Wrapper object to access the Flipper functionalities, similar wrapper for all controllers.
        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """
    _controller_units = 'binary position'

    _dvc = Thorlabs.list_kinesis_devices()
    serialnumbers = [d[0] for d in _dvc if d[1] == 'APT Filter Flipper']

    params= [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serialnumbers},
             {'title': 'Home Position:', 'name': 'home_position', 'type': 'list' , 'value': 0, 'limits' : [0,1]},
             {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group', 'visible': is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'limits': ['Master', 'Slave']},
                        {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'limits': stage_names},
                        ]
              }
             ]+comon_parameters


    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.settings.child('epsilon').setValue(0.1)
        self.settings.child('epsilon').setReadonly()

        self.settings.child('bounds', 'is_bounds').setValue(True)
        self.settings.child('bounds', 'is_bounds').setReadonly()

        self.settings.child('bounds', 'max_bound').setValue(1)
        self.settings.child('bounds', 'max_bound').setReadonly()

        self.settings.child('bounds', 'min_bound').setValue(0)
        self.settings.child('bounds', 'min_bound').setReadonly()

        self.settings.child('scaling','use_scaling').setValue(False)
        self.settings.child('scaling','use_scaling').setReadonly()
        self.settings.child('scaling','scaling').setValue(1)
        self.settings.child('scaling','scaling').setReadonly()
        self.settings.child('scaling','offset').setValue(0)
        self.settings.child('scaling','offset').setReadonly()

    def commit_settings(self,param):
        """
            | Activate any parameter changes on the hardware.
            | Called after a param_tree_changed signal received from DAQ_Move_main.

            =============== ================================ ========================
            **Parameters**  **Type**                          **Description**
            *param*         instance of pyqtgraph Parameter  The parameter to update
            =============== ================================ ========================
        """
        pass

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
                    controller = Thorlabs.kinesis.MFF(self.settings.child('serial_number').value())
                except:
                    raise Exception(f'No controller found with serial number {self.settings.child("serial_number").value()}')
                else:
                    self.controller = controller

            if not self.controller.is_opened():
                self.controller.open()

            #Getting the information from the device
            info = self.controller.get_device_info()

            #Setting the name of the controller == Type of controller
            self.settings.child('controller_id').setValue(info.notes)

            #Setting the transit time
            ttime_s = self.controller.get_flipper_parameters().transit_time
            self.settings.child('timeout').setValue(ttime_s*1e3) #Transit time ms

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
        self.controller=None

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
            Get the current hardware position with scaling conversion of the Kinesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        #Get position = 0 or 1, possibly None if unknown
        pos = self.controller.get_state()
        #Repollif pos returns none
        while pos == None:
            pos = self.controller.get_state()

        #This is superfluous as there is not scaling
        # pos = self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('check_position', [pos]))
        return pos

    def move_Abs(self,position):
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
        # superfluous because there is no scaling for a flipper
        # position = self.set_position_with_scaling(position)  # apply scaling if the user specified one

        # pos = self.check_position()
        # if pos == 0:
        #     position = 1
        # else:
        #     position = 0

        self.controller.move_to_state(position)
        self.emit_status(ThreadCommand('Update_Status', [f'Moving to position: {position}']))

        self.target_position = position
        self.poll_moving()


    def move_Rel(self,position):
        """ Move the actuator to the relative target actuator value defined by position
        Parameters
        ----------
        position: (float) value of the relative target positioning
        """
        self.current_position = self.check_position()
        # rel_move  = self.check_bound(self.current_position+position)-self.current_position
        new_pos = self.check_bound(self.current_position + position)
        self.target_position = new_pos

        # pos = self.check_position()
        # if pos == 0:
        #     position = 1
        # else:
        #     position = 0

        # self.target_position = position
        self.controller.move_to_state(new_pos)
        self.emit_status(ThreadCommand('Update_Status', [f'Moving to position: {position}']))
        self.poll_moving()


    def move_Home(self):
        """
            Make the absolute move to original position (0).
        """
        home = self.settings.child('home_position').value()
        self.target_position = home
        self.controller.move_to_state(home)
        self.emit_status(ThreadCommand('Update_Status', [f'Moving home: {home}']))
        self.poll_moving()