# -*- coding: utf-8 -*-
"""
Created the 15/06/2023

@author: Sebastien Weber
"""
from typing import Union, List
import pyvisa

from pymeasure.instruments.resources import list_resources
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun, main,
    DataActuatorType, DataActuator)  # common set of parameters for all actuators
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter

rm = pyvisa.ResourceManager()
com_ports = rm.list_resources()

logger = set_logger(get_module_name(__file__))

try:
    from pymeasure.instruments.thorlabs import thorlabs_elliptec as elliptec
    from pymeasure.instruments.thorlabs.elliptec_utils.base import scan_for_devices
except ImportError as e:
    logger.warning(str(e))


class DAQ_Move_ElliptecPyMeasure(DAQ_Move_base):
    """ Plugin for the Elliptec Piezo driven motors from thorlabs based on a pymeasure implementation => not yet published
    """
    _controller_units = '°'

    is_multiaxes = True
    _axis_names = [str(ind) for ind in range(4)]
    _epsilons = 0.1

    params = [ {'title': 'COM port', 'name': 'com_port', 'type': 'list', 'limits': com_ports},
               {'title': 'Device', 'name': 'device', 'type': 'str'},
               ] + comon_parameters_fun(axis_names=_axis_names, epsilon=_epsilons)
    data_actuator_type = DataActuatorType.DataActuator

    def ini_attributes(self):
        self.controller: elliptec.ElliptecController = None
        self.devices: list[str] = []

    def get_actuator_value(self) -> DataActuator:
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = DataActuator(self._title, data=self.controller.position, units=self.axis_unit)
        pos = self.get_position_with_scaling(pos)
        return pos

    def close(self):
        """Terminate the communication protocol"""
        self.controller.close()

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        pass

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
        self.devices = scan_for_devices(self.settings['com_port'], start_address=0, stop_address=4)
        if self.is_master:
            self.controller = elliptec.ElliptecController(self.settings['com_port'])
        else:
            self.controller = controller

        device = f'Motor:{self.devices[self.axis_index_key]["Motor Type"]} / '\
                 f'serial:{self.devices[self.axis_index_key]["Serial No."]}'
        self.settings.child('device').setValue(device)

        info = device
        initialized = True
        return info, initialized

    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """

        value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one

        self.controller.set_angle(value.value(self.axis_unit))

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_value + value) - self.current_value
        self.target_value = value + self.current_value
        value = self.set_position_relative_with_scaling(value)

        self.controller.shift_angle(value.value(self.axis_unit))

    def move_home(self):
        """Call the reference method of the controller"""
        self.controller.home()
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        pass


if __name__ == '__main__':
    main(__file__, init=False)


