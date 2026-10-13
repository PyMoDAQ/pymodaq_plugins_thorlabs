from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, main, comon_parameters_fun, DataActuatorType,
                                                          DataActuator)
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter

from pymodaq_plugins_thorlabs.hardware.kinesis import serialnumbers_integrated_stepper, IntegratedStepper


logger = set_logger(get_module_name(__file__))


class DAQ_Move_KinesisIntegratedStepper(DAQ_Move_base):
    """

    """
    supported_platforms = ('win32',)  # a Windows driver

    _controller_units = 'degree'
    _epsilons = 0.05

    is_multiaxes = False

    _axis_names = ['']

    params = [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
              {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list',
               'limits': serialnumbers_integrated_stepper},
              {'title': 'Backlash:', 'name': 'backlash', 'type': 'float', 'value': 0, },
              ] + comon_parameters_fun(axis_names=_axis_names, epsilon=_epsilons)
    data_actuator_type = DataActuatorType.DataActuator

    def ini_attributes(self):
        self.controller: IntegratedStepper = None
        self.settings.child('bounds', 'is_bounds').setValue(True)
        self.settings.child('bounds', 'max_bound').setValue(360)
        self.settings.child('bounds', 'min_bound').setValue(0)

    def commit_settings(self, param):
        if param.name() == 'backlash':
            self.controller.backlash = param.value()

    def ini_stage(self, controller=None):
        """
        """
        if self.is_master:
            self.controller = IntegratedStepper()
            self.controller.connect(self.settings['serial_number'])
        else:
            self.controller = controller

        info = self.controller.name
        self.settings.child('controller_id').setValue(info)

        self.controller.backlash = self.settings['backlash']

        initialized = True
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

    def get_actuator_value(self) -> DataActuator:
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """

        pos = DataActuator(self._title,
                           data=self.controller.get_position(),
                           units=self.axis_unit)
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position: DataActuator):
        """


        """
        position = self.check_bound(position)
        self.target_value = position
        position = self.set_position_with_scaling(position)

        self.controller.move_abs(position.value(self.axis_unit))

    def move_rel(self, position: DataActuator):
        """

        """
        position = self.check_bound(self.current_value + position) - self.current_value
        self.target_value = position + self.current_value
        position = self.set_position_relative_with_scaling(position)

        self.controller.move_rel(position.value(self.axis_unit))

    def move_home(self):
        """
        """
        self.controller.home(callback=self.move_done)


if __name__ == '__main__':
    main(__file__, init=False)
