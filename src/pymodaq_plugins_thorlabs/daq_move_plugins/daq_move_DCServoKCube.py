from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun, main, DataActuatorType, DataActuator)
from pymodaq.utils.daq_utils import ThreadCommand

from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_thorlabs.hardware.daq_move_servocube_abstract import DAQ_Move_DCServoCube_Abstract
from pymodaq_plugins_thorlabs.hardware.kinesis import DCServoKCube, serialnumbers_kcube_dcservo
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class DAQ_Move_DCServoKCube(DAQ_Move_DCServoCube_Abstract):
    """ Instrument plugin class for Thorlabs DC Servo TCube.

    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """

    # Controller type
    controller_type = DCServoKCube

    # Parameters
    _controller_units = DCServoKCube.default_units
    is_multiaxes = False
    _axes_names = ['']
    _epsilon = 0.005
    data_actuator_type = DataActuatorType.DataActuator
    params = [
                 {'title': 'Serial Number:', 'name': 'serial_number', 'type': 'list',
                  'limits': serialnumbers_kcube_dcservo, 'value': serialnumbers_kcube_dcservo[0]}

             ] + comon_parameters_fun(is_multiaxes, axes_names=_axes_names, epsilon=_epsilon)


if __name__ == '__main__':
    main(__file__, init=False)
