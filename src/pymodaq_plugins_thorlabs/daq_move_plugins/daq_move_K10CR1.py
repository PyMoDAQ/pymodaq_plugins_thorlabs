"""
Plugin for the K10CR1 Integrated Stepper motor for rotation
Its is using the Instrumental package with its kinesis driver (based from the C-libraries)
Thorlabs Kinesis drivers and SDKs should be installed and the path to where are located the dlls should be added to
the PATH system environment variable
"""

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main
from pymodaq.control_modules.move_utility_classes import comon_parameters
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo, find_dict_in_list_from_key_val
from easydict import EasyDict as edict
from instrumental.drivers.motion.kinesis import list_instruments
from instrumental import instrument

parameter_sets = list_instruments()
serialnumbers = [pset['serial'] for pset in parameter_sets if pset['classname'] == 'K10CR1']

class DAQ_Move_K10CR1(DAQ_Move_base):
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
    is_multiaxes = False

    stage_names = []

    params = [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
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
        self.settings.child('epsilon').setValue(0.005)


    def commit_settings(self, param):
        """
            | Activate any parameter changes on the hardware.
            | Called after a param_tree_changed signal received from DAQ_Move_main.

            =============== ================================ ========================
            **Parameters**  **Type**                          **Description**
            *param*         instance of pyqtgraph parameter  The parameter to update
            =============== ================================ ========================
        """
        pass

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

                self.controller = instrument(
                    find_dict_in_list_from_key_val(parameter_sets, 'serial',
                                                   self.settings.child('serial_number').value()))
                self.controller.backlash = '0deg'
            info = self.controller.get_info()
            self.settings.child('controller_id').setValue(info)

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
        self.controller.close()
        self.controller = None

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        self.controller.stop()
        self.move_done()

    def check_position(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos = self.controller.position.m_as('deg')
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

        self.controller.move_to(f'{position}deg', wait=False)
        #self.poll_moving()

    def move_Rel(self, position):
        """

        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position
        position = self.set_position_relative_with_scaling(position)
        self.controller.move_relative(f'{position}deg', wait=False)
        #self.poll_moving()

    def move_Home(self):
        """
            Make the absolute move to original position (0).
        """
        self.target_position = 0.
        self.controller.home()
        #self.poll_moving()


if __name__ == '__main__':
    main(__file__, init=False)