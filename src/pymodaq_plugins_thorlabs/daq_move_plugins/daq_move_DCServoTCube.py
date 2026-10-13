from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun, main, DataActuatorType, DataActuator)

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter

from pymodaq_plugins_thorlabs.hardware.daq_move_servocube_abstract import DAQ_Move_DCServoCube_Abstract
from pymodaq_plugins_thorlabs.hardware.kinesis import DCServoTCube, serialnumbers_tcube_dcservo


logger = set_logger(get_module_name(__file__))


class DAQ_Move_DCServoTCube(DAQ_Move_DCServoCube_Abstract):
    """ Instrument plugin class for Thorlabs DC Servo TCube.

    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """
    supported_platforms = ('win32',)  # a Windows driver

    # Controller type
    controller_type = DCServoTCube

    # Parameters
    _controller_units = DCServoTCube.default_units
    is_multiaxes = False
    _axis_names = ['']
    _epsilons = 0.005
    data_actuator_type = DataActuatorType.DataActuator
    params = [
                 {'title': 'Serial Number:', 'name': 'serial_number', 'type': 'list',
                  'limits': serialnumbers_tcube_dcservo, 'value': serialnumbers_tcube_dcservo[0] if len(serialnumbers_tcube_dcservo) > 0 else None,}

             ] + comon_parameters_fun(axis_names=_axis_names, epsilon=_epsilons)


if __name__ == '__main__':
    main(__file__, init=False)
