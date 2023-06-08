from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main, comon_parameters_fun
from pymodaq.utils.logger import set_logger, get_module_name

from pymodaq_plugins_thorlabs.hardware.kinesis import serialnumbers_flipper, Flipper

logger = set_logger(get_module_name(__file__))


class DAQ_Move_KinesisFlipper(DAQ_Move_base):
    """

    """
    _controller_units = 'degrees'
    _epsilon = 0.05

    is_multiaxes = False

    stage_names = []

    params = [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
              {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list',
               'limits': serialnumbers_flipper},
              ] + comon_parameters_fun(is_multiaxes, epsilon=_epsilon)

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
        self.controller = self.ini_stage_init(controller, Flipper())

        if self.settings['multiaxes', 'multi_status'] == "Master":
            self.controller.connect(self.settings['serial_number'])

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

    def get_actuator_value(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """

        pos = self.controller.get_position()
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position):
        """


        """
        position = self.check_bound(position)
        self.target_position = position
        position = self.set_position_with_scaling(position)

        self.controller.move_abs(position)

    def move_rel(self, position):
        """

        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position
        position = self.set_position_relative_with_scaling(position)

        self.controller.move_rel(position)

    def move_home(self):
        """
        """
        self.controller.home(callback=self.move_done)


if __name__ == '__main__':
    main(__file__, init=False)
