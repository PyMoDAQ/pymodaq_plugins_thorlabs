from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main, comon_parameters_fun, DataActuatorType
#from pymodaq.utils.daq_utils import ThreadCommand
#from pymodaq.utils.parameter import Parameter
from pymodaq.utils.logger import set_logger, get_module_name

from pymodaq_plugins_thorlabs.hardware.kinesis import serialnumbers_piezo, Piezo


logger = set_logger(get_module_name(__file__))


class DAQ_Move_KPZ101(DAQ_Move_base):
    """
    Wrapper object to access Piezo functionalities, similar to Kinesis instruments 
    """
    _controller_units = 'V'
    _axes_names = {"X-axis"}
    _epsilon = 0.01
    data_actuator_type = DataActuatorType.DataActuator

    is_multiaxes = False
    logger.error('This plugin is not yet compatible with multi-axes')

    params = [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
              {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list',
               'limits': serialnumbers_piezo},
              ] + comon_parameters_fun(is_multiaxes, epsilon=_epsilon)

    def ini_attributes(self):
        try:
            self.controller: Piezo = None
            self.settings.child('bounds', 'is_bounds').setValue(True)
            self.settings.child('bounds', 'max_bound').setValue(360)
            self.settings.child('bounds', 'min_bound').setValue(0)
        except Exception as e: 
            logger.exception(str(e) + ' in DAQ_Move_KPZ101.ini_attributes')

    def commit_settings(self, param):
       pass 

    def ini_stage(self, controller=None):
        """
        Connect to Kinesis Piezo Stage by communicating with kinesis.py
        """
        self.controller = self.ini_stage_init(controller, Piezo())

        try :
            self.controller.connect(self.settings.child('serial_number').value())
        except Exception as e:
            logger.exception(str(e) + ' in DAQ_Move_KPZ101.ini_stage')

        # if self.settings['multiaxes', 'multi_status'] == "Master":
        #     self.controller.connect(self.settings(['serial_number']))
        try: 
            info = self.controller.name
            self.settings.child('controller_id').setValue(info)
        except Exception as e:
            logger.exception(str(e) + ' in DAQ_Move_KPZ101.ini_stage')
        # info = self.controller.name
        # self.settings.child('controller_id').setValue(info)
        try:
            initialized = True
        except Exception as e:
            logger.exception(str(e) + ' in DAQ_Move_KPZ101.ini_stage')
            initialized = False
        # initialized = True
        return info, initialized

    def close(self):
        """
            close the current instance of Kinesis instrument.
        """
        if self.controller is not None:
            self.controller.close()

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        if self.controller is not None:
            self.controller.stop()

    def get_actuator_value(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis instrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        
        pos = self.controller.get_position()
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position):
        """
        Set the current position with voltage conversion of the Kinesis instrument 
        """
        
        position = self.check_bound(position)
        self.target_position = position
        position = self.set_position_with_scaling(position)

        self.controller.move_abs(position) 

    def move_rel(self, position):
        """
        Moves the Kinesis Piezo Stage relatively to the current position. 
        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position
        position = self.set_position_relative_with_scaling(position)

        self.controller.move_abs(self.target_position)

    def move_home(self):
        """
        Move the Kinesis Piezo Stage to home position
        """
        self.controller.home(callback=self.move_done)


if __name__ == '__main__':
    main(__file__, init=False)
