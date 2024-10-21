from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun, main, DataActuatorType, DataActuator)
from pymodaq.utils.daq_utils import ThreadCommand

from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_thorlabs.hardware.kinesis import BrushlessDCMotor, serialnumbers_brushless
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class DAQ_Move_BrushlessDCMotor(DAQ_Move_base):
    """ Instrument plugin class for an actuator.

    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """
    _controller_units = BrushlessDCMotor.default_units
    is_multiaxes = True
    _axes_names = {'1': 1, '2': 2, '3': 3}
    _epsilon = 0.01
    data_actuator_type = DataActuatorType.DataActuator
    params = [
                 {'title': 'Serial Number:', 'name': 'serial_number', 'type': 'list',
                  'limits': serialnumbers_brushless, 'value': serialnumbers_brushless[0]}

             ] + comon_parameters_fun(is_multiaxes, axes_names=_axes_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.controller: BrushlessDCMotor = None
        self._move_done = False

    def move_done_callback(self, val: int):
        """ will be triggered for each end of move: abs, rel or homing"""
        self._move_done = True
        self.stop_motion()
        logger.debug('Callback called')

    def user_condition_to_reach_target(self) -> bool:
        """ Implement a condition for exiting the polling mechanism and specifying that the
        target value has been reached

       Returns
        -------
        bool: if True, PyMoDAQ considers the target value has been reached
        """

        return self._move_done

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = DataActuator(
            data=self.controller.get_position(self.axis_value),
            units=self.controller.get_units(self.axis_value)
        )
        pos = self.get_position_with_scaling(pos)
        return pos

    def close(self):
        """Terminate the communication protocol"""
        if self.is_master:
            self.controller.close()

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == 'axis':
            self.axis_unit = self.controller.get_units(self.axis_value)
            # update the units are they are not known before hand in the driver class but only
            # after initialization of the controller

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        if self.is_master:
            self.controller = BrushlessDCMotor()
            self.controller.connect(self.settings['serial_number'])
        else:
            self.controller = controller

        # update the axis unit by interogating the controller and the specific axis
        self.axis_unit = self.controller.get_units(self.axis_value)

        if not self.controller.is_homed(self.axis_value):
            self.move_home()

        info = f'{self.controller.name} - {self.controller.serial_number}'
        initialized = True
        return info, initialized

    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """
        self._move_done = False
        value = self.check_bound(value)
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one
        self.controller.move_abs(value.value(), channel=self.axis_value,
                                 callback=self.move_done_callback)

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        self._move_done = False
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)
        self.controller.move_abs(self.target_value.value(), channel=self.axis_value,
                                 callback=self.move_done_callback)

    def move_home(self):
        """Call the reference method of the controller"""
        self._move_done = False
        self.controller.home(channel=self.axis_value, callback=self.move_done_callback)

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""

        self.controller.stop(self.axis_value)


if __name__ == '__main__':
    main(__file__, init=False)
