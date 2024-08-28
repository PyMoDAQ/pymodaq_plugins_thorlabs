# Purpose: Control the KPZ101 piezo stage from Thorlabs with PyMoDAQ plugin
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main, DataActuatorType,\
    DataActuator  # common set of parameters for all actuators
from pymodaq.utils.daq_utils import ThreadCommand # object used to send info back to the main thread
from pymodaq.utils.parameter import Parameter
#from pymeasure.instruments.thorlabs import KPZ101

import clr
clr.AddReference(r"C:\Program Files\Thorlabs\Kinesis\Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference(r"C:\Program Files\Thorlabs\Kinesis\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference(r"C:\Program Files\Thorlabs\Kinesis\Thorlabs.MotionControl.GenericPiezoCLI.dll")
clr.AddReference(r"C:\Program Files\Thorlabs\Kinesis\Thorlabs.MotionControl.KCube.PiezoCLI.dll")

from Thorlabs.MotionControl.DeviceManagerCLI import * 
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.GenericPiezoCLI import *
from Thorlabs.MotionControl.KCube.PiezoCLI import *
from System import Decimal
import time
from os import system

# TODO:
# (1) change the name of the following class to DAQ_Move_TheNameOfYourChoice
# (2) change the name of this file to daq_move_TheNameOfYourChoice ("TheNameOfYourChoice" should be the SAME
#     for the class name and the file name.)
# (3) this file should then be put into the right folder, namely IN THE FOLDER OF THE PLUGIN YOU ARE DEVELOPING:
#     pymodaq_plugins_my_plugin/daq_move_plugins
class DAQ_Move_KPZ101(DAQ_Move_base):
    """ KPZ101 plugin class for an actuator.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    TODO Complete the docstring of your plugin with:
        * The set of controllers and actuators that should be compatible with this instrument plugin.
        * With which instrument and controller it has been tested.
        * The version of PyMoDAQ during the test.
        * The version of the operating system.
        * Installation instructions: what manufacturer’s drivers should be installed to make it run?

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
         
    # TODO add your particular attributes here if any

    """
    _controller_units = 'V'
    is_multiaxes = False  # TODO for your plugin set to True if this plugin is controlled for a multiaxis controller
    _axis_names = ['Voltage'] 
    _epsilon = 0  # TODO replace this by a value that is correct depending on your controller
    data_actuator_type = DataActuatorType['float']  # wether you use the new data style for actuator otherwise set this
    # as  DataActuatorType['float']  (or entirely remove the line)

    params = [{'title': 'KPZ101 Parameters', 'name': 'KPZ101'}] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)
    # _epsilon is the initial default value for the epsilon parameter allowing pymodaq to know if the controller reached
    # the target value. It is the developer responsibility to put here a meaningful value

    def ini_attributes(self):
        DeviceManagerCLI.BuildDeviceList()
        serial_number = '29252556' #must add serial number
        self.controller = KCubePiezo.CreateKCubePiezo(serial_number)

        self.controller.Connect(serial_number)

        info_device = self.controller.GetDeviceInfo()

        self.controller.StartPolling(250)
        time.sleep(0.25)

        self.controller.EnableDevice()
        time.sleep(0.25) 

        # device_config = self.controller.GetPiezoConfiguration(serial_number)

        # device_settings = self.controller.PiezoDeviceSettings

    def get_voltage_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = DataActuator(data=self.controller.GetOutputVoltage())  # when writing your own plugin replace this line
        pos = self.get_position_with_scaling(pos)
        return pos

    def close(self):
        """Terminate the communication protocol"""
        self.controller.disconnect()
        #  self.controller.your_method_to_terminate_the_communication()  # when writing your own plugin replace this line

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == "voltage":
            voltage = Decimal(voltage)
            min_volt = System.Decimal(0)
            max_volt = self.controller.GetMaxOutputVoltage()
            if voltage != min_volt and voltage <= max_volt:
                self.device.SetOutputVoltage(voltage)
                time.sleep(1.0)
            else:
                self.emit_status(ThreadCommand('Update_Status', ['Voltage out of range']))     
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
 
        self.controller = self.ini_stage_init(old_controller=controller,
                                              new_controller=KPZ101())
        info = "Moving stage KPZ101"
        initialized = self.controller  # todo
        return info, initialized

    def move_home(self):
        """Call the reference method of the controller"""
        self.controller.SetZero() 
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    def stop_motion(self):
      """Stop the actuator and emits move_done signal"""
      self.controller.disconnect() 
      self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))


if __name__ == '__main__':
    main(__file__)



# Below is extra lines of code that can be used for moving the actuator
       # def move_abs(self, value: DataActuator):
    #     """ Move the actuator to the absolute target defined by value

    #     Parameters
    #     ----------
    #     value: (float) value of the absolute target positioning
    #     """

    #     value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
    #     self.target_value = value
    #     value = self.set_position_with_scaling(value)  # apply scaling if the user specified one
    #     ## TODO for your custom plugin
    #     raise NotImplemented  # when writing your own plugin remove this line
    #     self.controller.your_method_to_set_an_absolute_value(value.value())  # when writing your own plugin replace this line
    #     self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    # def move_rel(self, value: DataActuator):
    #     """ Move the actuator to the relative target actuator value defined by value

    #     Parameters
    #     ----------
    #     value: (float) value of the relative target positioning
    #     """
    #     value = self.check_bound(self.current_position + value) - self.current_position
    #     self.target_value = value + self.current_position
    #     value = self.set_position_relative_with_scaling(value)

    #     ## TODO for your custom plugin
    #     raise NotImplemented  # when writing your own plugin remove this line
    #     self.controller.your_method_to_set_a_relative_value(value.value())  # when writing your own plugin replace this line
    #     self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
