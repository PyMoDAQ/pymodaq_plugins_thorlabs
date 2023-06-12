from easydict import EasyDict as edict
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from instrumental import instrument, list_instruments, Q_

# This is a (probably bad) way of importing the stuff needed to get exposure range
import instrumental.drivers.cameras.uc480 as uc480module


class DAQ_2DViewer_Thorlabs_DCx(DAQ_Viewer_base):
    """This plugin is intended for Thorlabs DCx cameras series.
        It should not be compatible with Thorlabs scientific cameras.

        This plugin use the instrumental library:
        https://instrumental-lib.readthedocs.io/en/stable/

        The class we use is defined here:
        https://github.com/mabuchilab/Instrumental/blob/master/instrumental/drivers/
        cameras/uc480.py

        Prerequisite
        ------------
        This plugin works with Windows 10.
        Installation procedure can be found here:
            https://instrumental-lib.readthedocs.io/en/stable/uc480-cameras.html
        In particular, the ThorCam software should be installed and the .dll libraries
            folder (where you can find uc480_64.dll) should be added in the environment
            PATH variable.
        In principle the dependencies (pywin32, nicelib) should be installed
            automatically while installing the plugin.
    """

    # Look for plugged cameras and get the serial numbers
    plugged_cameras = list_instruments(module='cameras.uc480')
    serial_numbers = []
    for paramset in plugged_cameras:
        camera = instrument(paramset, reopen_policy='reuse')
        serial_numbers.append(camera.serial.decode("utf-8"))

    params = comon_parameters + [
        {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serial_numbers},
        {'title': 'Exposure (ms):', 'name': 'exposure', 'type': 'float', 'value': 0},
        {'title': 'Gain:', 'name': 'master_gain', 'type': 'int', 'value': 0, "limits": [0, 100]},
        {'title': 'Gain Boost:', 'name': 'gain_boost', 'type': 'bool', 'value': False},
        {'title': 'gamma', 'name': 'gamma', 'type': 'int', 'value': 0},
        {'title': 'Color Mode', 'name': 'colormode', 'type': 'str', 'value': 'mono8', "readonly": True},
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

        self.x_axis = None
        self.y_axis = None

        self.controller = None

    def commit_settings(self, param):
        """
        """
        if param.name() == 'exposure':
            # For some reason exposure is dealt specially in the instrumental lib
            self.controller._set_exposure(Q_(param.value(), 'ms'))
            self.settings.child('exposure').setValue(self.controller._get_exposure().m_as('ms'))
        elif param.name() in ['master_gain', 'gain_boost', 'gamma']:
            # All settings without units can be dealt as a single case
            setattr(self.controller, param.name(), param.value())
            self.settings.child(param.name()).setValue(getattr(self.controller, param.name()))

    def ini_detector(self, controller=None):
        """Detector communication initialization
        Parameters
        ----------
        controller: (object) custom object of a PyMoDAQ plugin (Slave case).
            None if only one detector by controller (Master case)
        Returns
        -------
        self.status (edict): with initialization status: three fields:
            * info (str)
            * controller (object) initialized controller
            * initialized: (bool): False if initialization failed otherwise True
        """

        try:
            self.status.update(edict(initialized=False, info="", x_axis=None,
                                     y_axis=None, controller=None))
            if self.settings.child('controller_status').value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while'
                                    'this detector is a slave one')
                else:
                    self.controller = controller
            else:
                camera_serial = self.settings.child('serial_number').value()
                plugged_cameras = list_instruments(module='cameras.uc480')
                selected_camera = None
                # Find the paramset that has the selected serial number
                for paramset in plugged_cameras:
                    camera = instrument(paramset, reopen_policy='reuse')
                    if camera.serial.decode("utf-8") == camera_serial:
                        selected_camera = camera

                self.controller = selected_camera

                # Getting the current settings from the instrument.
                # Exposure is weird
                self.settings.child('exposure').setValue(self.controller._get_exposure().m_as('ms'))
                for paraname in ['master_gain', 'gain_boost', 'gamma']:
                    paramvalue = getattr(self.controller, paraname)
                    self.settings.child(paraname).setValue(paramvalue)

                # Getting the range of exposure possible. I think it changes with other settings of the camera so it's
                # probably not ideal to set it like this. The _dev calls are needed because instrumental does not
                # natively exposes these parameters like it does e.g. for _get_exposure()

                rangemin = self.controller._dev.Exposure(uc480module.lib.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MIN)
                rangemax = self.controller._dev.Exposure(uc480module.lib.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MAX)
                self.settings.child('exposure').setOpts(limits=[rangemin, rangemax])

            self.status.info = "Detector initialized"
            self.status.initialized = True
            self.status.controller = self.controller
            return self.status

        except Exception as e:
            self.emit_status(
                ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def close(self):
        """
        Terminate the communication protocol
        """
        self.controller.close()

    def grab_data(self, Naverage=1, **kwargs):
        """
        Parameters
        ----------
        Naverage: (int) Number of hardware averaging
        kwargs: (dict) of others optionals arguments
        """
        #The instrumental library seems really broken AF unfortunately so I have to use this to acquire a frame otherwise
        #it just uses the default values...
        kwds = {'exposure_time': Q_(self.settings.child('exposure').value(), 'ms'),
                'gain': self.settings.child('master_gain').value()}

        data = self.controller.grab_image(**kwds)

        if len(data.shape) > 2:
            data_list = [data[..., ind] for ind in range(data.shape[2])]
        else:
            data_list = [data]

        # data = self.controller.grab_image(exposure_time=Q_(self.settings.child('exposure').value(), 'ms'))
        self.data_grabed_signal.emit([DataFromPlugins(name='Thorcam', data=data_list,
                                                      dim='Data2D')])

    def stop(self):

        self.controller.stop_live_video()
        # self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        return ''


if __name__ == '__main__':
    main(__file__, init=False)