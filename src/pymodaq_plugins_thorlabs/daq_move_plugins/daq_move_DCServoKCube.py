from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base, comon_parameters_fun, main, DataActuatorType, DataActuator)

from pymodaq_plugins_thorlabs.daq_move_plugins.daq_move_DCServoTCube import DAQ_Move_DCServoTCube
from pymodaq_plugins_thorlabs.hardware.kinesis import DCServoKCube, serialnumbers_kcube_dcservo

from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))


class DAQ_Move_DCServoKCube(DAQ_Move_DCServoTCube):
    """ Instrument plugin class for Kinesis KCube devices.
    All functionality is adapted from DAQ_Move_DCServoTCube. 

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """
    _controller_units = DCServoKCube.default_units
    params = [
                 {'title': 'Serial Number:', 'name': 'serial_number', 'type': 'list',
                  'limits': serialnumbers_kcube_dcservo, 'value': serialnumbers_kcube_dcservo[0]}

             ] + comon_parameters_fun(DAQ_Move_DCServoTCube.is_multiaxes,
                                      axes_names=DAQ_Move_DCServoTCube._axes_names,
                                      epsilon=DAQ_Move_DCServoTCube._epsilon)


    def ini_attributes(self):
        self.controller: DCServoKCube = None
        self._move_done = False


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
            self.controller = DCServoKCube()
            self.controller.connect(self.settings['serial_number'])
        else:
            self.controller = controller

        # update the axis unit by interogating the controller and the specific axis
        self.axis_unit = self.controller.get_units()

        if not self.controller.is_homed:
            self.move_home()

        info = f'{self.controller.name} - {self.controller.serial_number}'
        initialized = True
        return info, initialized


if __name__ == '__main__':
    main(__file__, init=False)
