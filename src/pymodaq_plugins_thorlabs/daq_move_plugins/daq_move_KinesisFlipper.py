from pymodaq.control_modules.daq_move_ui.utils import UiType
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main, comon_parameters_fun, DataActuatorType
from pymodaq.utils.data import DataActuator
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter

from pymodaq_plugins_thorlabs.hardware.kinesis import serialnumbers_flipper, Flipper

logger = set_logger(get_module_name(__file__))


class DAQ_Move_KinesisFlipper(DAQ_Move_base):
    """

    """
    supported_platforms = ('win32',)  # a Windows driver

    _controller_units = ''
    _epsilons = 0.05

    is_multiaxes = False

    _axis_names = ['']

    params = [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
              {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list',
               'limits': serialnumbers_flipper},
              ] + comon_parameters_fun(axis_names=_axis_names, epsilon=_epsilons)

    ui_type = UiType.BINARY
    data_actuator_type = DataActuatorType.DataActuator

    def ini_attributes(self):
        self.controller: Flipper = None
        self.settings.child('bounds', 'is_bounds').setValue(True)
        self.settings.child('bounds', 'max_bound').setValue(1)
        self.settings.child('bounds', 'min_bound').setValue(0)

    def commit_settings(self, param):
        if param.name() == 'backlash':
            self.controller.backlash = param.value()

    def ini_stage(self, controller=None):
        """
        """
        if self.is_master:
            self.controller = Flipper()
            self.controller.connect(self.settings['serial_number'])
        else:
            self.controller = controller

        info = self.controller.name
        self.settings.child('controller_id').setValue(info)

        initialized = True
        return info, initialized

    def close(self):
        """
            close the current instance of Kinesis instrument.
        """
        self.controller.close()

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        self.controller.stop()

    def get_actuator_value(self) -> DataActuator:
        """

        """

        pos = DataActuator(self._title, data=self.controller.get_position())
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position: DataActuator):
        """


        """
        position = self.check_bound(position)
        self.target_value= position
        position = self.set_position_with_scaling(position)

        self.controller.move_abs(position.value())

    def move_rel(self, position: DataActuator):
        """

        """
        position = self.check_bound(self.current_value + position) - self.current_value
        self.target_value = position + self.current_value
        position = self.set_position_relative_with_scaling(position)

        self.controller.move_rel(position.value())

    def move_home(self):
        """
        """
        self.controller.home(callback=self.move_done)


if __name__ == '__main__':
    main(__file__, init=False)
