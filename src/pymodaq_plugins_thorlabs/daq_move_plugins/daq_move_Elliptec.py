# -*- coding: utf-8 -*-
"""
Created the 15/06/2023

@author: Sebastien Weber
"""

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main  # common set of parameters for all actuators
from pymodaq.utils.daq_utils import ThreadCommand # object used to send info back to the main thread
from pymodaq.utils.parameter import Parameter

from elliptec import Controller, Rotator
from elliptec.scan import find_ports, scan_for_devices

com_ports = find_ports()


class DAQ_Move_Elliptec(DAQ_Move_base):
    """Plugin for the Template Instrument

    This object inherits all functionality to communicate with PyMoDAQ Module through inheritance via DAQ_Move_base
    It then implements the particular communication with the instrument

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library

    """
    _controller_units = 'whatever'
    is_multiaxes = True
    axes_names = ['0']
    _epsilon = 0.1

    params = [ {'title': 'COM port', 'name': 'com_port', 'type': 'list', 'limits': com_ports},
               {'title': 'Serial No.', 'name': 'serial', 'type': 'str'},
               {'title': 'Motor Type', 'name': 'motor', 'type': 'str'},
               {'title': 'Range', 'name': 'range', 'type': 'str'},
               ] + comon_parameters_fun(is_multiaxes, axes_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.controller: Rotator = None

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = self.controller.get_angle()
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
        serial = Controller(self.settings['com_port'])
        self.controller = self.ini_stage_init(old_controller=controller,
                                              new_controller=Rotator(serial))
        all_info = self.controller.get('info')
        self.settings.child('serial').setValue(all_info['Serial No.'])
        self.settings.child('motor').setValue(all_info['Motor Type'])
        self.settings.child('range').setValue(all_info['Range'])
        """
        info = {'Address': addr,
                'Motor Type': int(msg[3:5], 16),
                'Serial No.': msg[5:13],
                'Year': msg[13:17],
                'Firmware': msg[17:19],
                'Thread': is_metric(msg[19]),
                'Hardware': msg[20],
                'Range': (int(msg[21:25], 16)),
                'Pulse/Rev': (int(msg[25:], 16))}
        """
        info = str(all_info)
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


