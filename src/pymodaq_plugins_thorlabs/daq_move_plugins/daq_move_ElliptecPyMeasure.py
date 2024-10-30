# -*- coding: utf-8 -*-
"""
Created the 15/06/2023

@author: Sebastien Weber
"""
from typing import Union, List
import pyvisa

from pymeasure.instruments.thorlabs import thorlabs_elliptec as elliptec
from pymeasure.instruments.thorlabs.elliptec_utils.base import scan_for_devices
from pymeasure.instruments.resources import list_resources
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main  # common set of parameters for all actuators
from pymodaq.utils.daq_utils import ThreadCommand  # object used to send info back to the main thread
from pymodaq.utils.parameter import Parameter

rm = pyvisa.ResourceManager()
com_ports = rm.list_resources()


class DAQ_Move_ElliptecPyMeasure(DAQ_Move_base):
    """ Plugin for the Elliptec Piezo driven motors from thorlabs

    This object inherits all functionality to communicate with PyMoDAQ Module through inheritance via DAQ_Move_base
    It then implements the particular communication with the instrument

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library

    """
    _controller_units = ''

    is_multiaxes = True
    axes_names = [str(ind) for ind in range(4)]
    _epsilon = 0.1

    params = [ {'title': 'COM port', 'name': 'com_port', 'type': 'list', 'limits': com_ports},
               {'title': 'Device', 'name': 'device', 'type': 'str'},
               ] + comon_parameters_fun(is_multiaxes, axes_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.controller: elliptec.ElliptecController = None
        self.devices: List[str] = []

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = self.controller.position
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
        ## TODO for your custom plugin
        if param.name() == "a_parameter_you've_added_in_self.params":
           self.controller.your_method_to_apply_this_param_change()
        else:
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

        self.controller = self.ini_stage_init(old_controller=controller,
                                              new_controller=elliptec.ElliptecController(self.settings['com_port']))
        address = int(self.settings['multiaxes', 'axis'])
        device = f'Motor:{self.devices[address]["Motor Type"]} / '\
                 f'serial:{self.devices[address]["Serial No."]}'
        self.settings.child('device').setValue(device)


        info = device
        initialized = True
        return info, initialized

    def move_abs(self, value):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """

        value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one

        self.controller.set_angle(value)  # when writing your own plugin replace this line

    def move_rel(self, value):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)

        self.controller.shift_angle(value)  # when writing your own plugin replace this line

    def move_home(self):
        """Call the reference method of the controller"""
        self.controller.home()  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        pass


if __name__ == '__main__':
    main(__file__, init=False)


