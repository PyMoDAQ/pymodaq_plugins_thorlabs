import cv2
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from pylablib.devices import Thorlabs
from qtpy import QtWidgets, QtCore
import numpy as np
from time import perf_counter


class DAQ_2DViewer_Thorlabs_TSI(DAQ_Viewer_base):
    """
    Plugin for Thorlabs scientific sCMOS cameras such as Kiralux or Zelux. It has been tested with Thorlabs Zelux camera on Windows.
    Building on pylablib driver, information about it can be found here : https://pylablib.readthedocs.io/en/stable/devices/Thorlabs_TLCamera.html

    As in pylablib, the plugin will look for DLLs in the default Thorcam installation folder. Specifying a custom DLL folder is not implemented yet.

    The plugin provides binning functionality as well as ROI (region of interest) selection, which are on handled the hardware side.
    To use ROIs, click on "Show/Hide ROI selection area" in the viewer panel (icon with dashed rectangle).
    Position the rectangle as you wish, either with mouse or by entering coordinates, then click "Update ROI" button.

    The "Clear ROI+Bin" button resets to default cameras parameters: no binning and full frame.
    """

    serialnumbers = Thorlabs.list_cameras_tlcam()

    params = comon_parameters + [
        {'title': 'Camera name:', 'name': 'camera_name', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serialnumbers},
        #{'title': 'Sensor type:', 'name': 'sensor', 'type': 'str', 'value': '', 'readonly': True},
        #this will be used once pylablib accepts PR52
        {'title': 'Sensor type:', 'name': 'sensor', 'type': 'list', 'limits': ['Monochrome', 'Bayer']},
        {'title': 'Ouput Color:', 'name': 'output_color', 'type': 'list', 'limits': ['RGB', 'MonoChrome']},
        {'title': 'Update ROI', 'name': 'update_roi', 'type': 'bool_push', 'value': False},
        {'title': 'Clear ROI+Bin', 'name': 'clear_roi', 'type': 'bool_push', 'value': False},
        {'title': 'X binning', 'name': 'x_binning', 'type': 'int', 'value': 1},
        {'title': 'Y binning', 'name': 'y_binning', 'type': 'int', 'value': 1},
        {'title': 'Image width', 'name': 'hdet', 'type': 'int', 'value': 1, 'readonly': True},
        {'title': 'Image height', 'name': 'vdet', 'type': 'int', 'value': 1, 'readonly': True},
        {'title': 'Timing', 'name': 'timing_opts', 'type': 'group', 'children':
            [{'title': 'Exposure Time (ms)', 'name': 'exposure_time', 'type': 'int', 'value': 1},
            {'title': 'Compute FPS', 'name': 'fps_on', 'type': 'bool', 'value': True},
            {'title': 'FPS', 'name': 'fps', 'type': 'float', 'value': 0.0, 'readonly': True}]
        }
    ]

    callback_signal = QtCore.Signal()

    def ini_attributes(self):
        self.controller: Thorlabs.ThorlabsTLCamera = None

        self.x_axis = None
        self.y_axis = None
        self.last_tick = 0.0  # time counter used to compute FPS
        self.fps = 0.0

        self.data_shape: str = ''
        self.callback_thread = None

        # Disable "use ROI" option to avoid confusion with other buttons
        #self.settings.child('ROIselect', 'use_ROI').setOpts(visible=False)

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == "exposure_time":
            self.controller.set_exposure(param.value()/1000)

        if param.name() == "fps_on":
            self.settings.child('timing_opts', 'fps').setOpts(visible=param.value())

        if param.name() == "update_roi":
            if param.value():   # Switching on ROI

                # We handle ROI and binning separately for clarity
                (old_x, _, old_y, _, xbin, ybin) = self.controller.get_roi() # Get current binning

                # Values need to be rescaled by binning factor and shifted by current x0,y0 to be correct.
                new_x = (old_x + self.settings.child('ROIselect', 'x0').value())*xbin
                new_y = (old_y + self.settings.child('ROIselect', 'y0').value())*xbin
                new_width = self.settings.child('ROIselect', 'width').value()*ybin
                new_height = self.settings.child('ROIselect', 'height').value()*ybin

                new_roi = (new_x, new_width, xbin, new_y, new_height, ybin)
                self.update_rois(new_roi)
                # recenter rectangle
                self.settings.child('ROIselect', 'x0').setValue(0)
                self.settings.child('ROIselect', 'y0').setValue(0)
                param.setValue(False)

        if param.name() in ['x_binning', 'y_binning']:
            # We handle ROI and binning separately for clarity
            (x0, w, y0, h, *_) = self.controller.get_roi()  # Get current ROI
            xbin = self.settings.child('x_binning').value()
            ybin = self.settings.child('y_binning').value()
            new_roi = (x0, w, xbin, y0, h, ybin)
            self.update_rois(new_roi)

        if param.name() == "clear_roi":
            if param.value():   # Switching on ROI
                wdet, hdet = self.controller.get_detector_size()
                # self.settings.child('ROIselect', 'x0').setValue(0)
                # self.settings.child('ROIselect', 'width').setValue(wdet)
                self.settings.child('x_binning').setValue(1)
                #
                # self.settings.child('ROIselect', 'y0').setValue(0)
                # new_height = self.settings.child('ROIselect', 'height').setValue(hdet)
                self.settings.child('y_binning').setValue(1)

                new_roi = (0, wdet, 1, 0, hdet, 1)
                self.update_rois(new_roi)
                param.setValue(False)

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        # Initialize camera class
        if not self.settings.child('serial_number').value() == '':
            self.ini_detector_init(old_controller=controller,
                                   new_controller=Thorlabs.ThorlabsTLCamera(self.settings.child('serial_number').value()))
        else:
            raise Exception('No compatible Thorlabs scientific camera was found.')

        device_info = self.controller.get_device_info()

        # Get camera name
        self.settings.child('camera_name').setValue(device_info.name)

        # this will be used once pylablib accepts PR52
        # # Get Sensor Type
        # self.settings.child('sensor').setValue(device_info.sensor_type)

        if 'monochrome' in self.settings['sensor'].lower():
            self.settings.child('output_color').setValue('MonoChrome')
            self.settings.child('output_color').setOpts(visible=False)

        # Set exposure time
        self.controller.set_exposure(self.settings.child('timing_opts', 'exposure_time').value()/1000)

        # FPS visibility
        self.settings.child('timing_opts', 'fps').setOpts(visible=self.settings.child('timing_opts', 'fps_on').value())

        # Update image parameters
        (*_, hbin, vbin) = self.controller.get_roi()
        height, width = self.controller.get_data_dimensions()
        self.settings.child('x_binning').setValue(hbin)
        self.settings.child('y_binning').setValue(vbin)
        self.settings.child('hdet').setValue(width)
        self.settings.child('vdet').setValue(height)

        # Way to define a wait function with arguments
        wait_func = lambda: self.controller.wait_for_frame(since='lastread', nframes=1, timeout=20.0)
        callback = ThorlabsCallback(wait_func)

        self.callback_thread = QtCore.QThread()  # creation of a Qt5 thread
        callback.moveToThread(self.callback_thread)  # callback object will live within this thread
        callback.data_sig.connect(
            self.emit_data)  # when the wait for acquisition returns (with data taken), emit_data will be fired

        self.callback_signal.connect(callback.wait_for_acquisition)
        self.callback_thread.callback = callback
        self.callback_thread.start()

        self._prepare_view()

        info = "Initialized camera"
        initialized = True
        return info, initialized

    def _prepare_view(self):
        """Preparing a data viewer by emitting temporary data. Typically, needs to be called whenever the
        ROIs are changed"""
        # wx = self.settings.child('rois', 'width').value()
        # wy = self.settings.child('rois', 'height').value()
        # bx = self.settings.child('rois', 'x_binning').value()
        # by = self.settings.child('rois', 'y_binning').value()
        #
        # sizex = wx // bx
        # sizey = wy // by
        height, width = self.controller.get_data_dimensions()

        self.settings.child('hdet').setValue(width)
        self.settings.child('vdet').setValue(height)
        mock_data = np.zeros((height, width))

        if width != 1 and height != 1:
            data_shape = 'Data2D'
        else:
            data_shape = 'Data1D'

        if data_shape != self.data_shape:
            self.data_shape = data_shape
            # init the viewers
            self.data_grabed_signal_temp.emit([DataFromPlugins(name='Thorlabs Camera',
                                                               data=[np.squeeze(mock_data)],
                                                               dim=self.data_shape,
                                                               labels=[f'ThorCam_{self.data_shape}'])])
            QtWidgets.QApplication.processEvents()

    def update_rois(self, new_roi):
        # In pylablib, ROIs compare as tuples
        (new_x, new_width, new_xbinning, new_y, new_height, new_ybinning) = new_roi
        if new_roi != self.controller.get_roi():
            # self.controller.set_attribute_value("ROIs",[new_roi])
            self.controller.set_roi(hstart=new_x, hend=new_x + new_width, vstart=new_y, vend=new_y + new_height,
                                    hbin=new_xbinning, vbin=new_ybinning)
            self.emit_status(ThreadCommand('Update_Status', [f'Changed ROI: {new_roi}']))
            self.controller.clear_acquisition()
            self.controller.setup_acquisition()
            # Finally, prepare view for displaying the new data
            self._prepare_view()

    def grab_data(self, Naverage=1, **kwargs):
        """
        Grabs the data. Synchronous method (kinda).
        ----------
        Naverage: (int) Number of averaging
        kwargs: (dict) of others optionals arguments
        """
        try:
            # Warning, acquisition_in_progress returns 1,0 and not a real bool
            if not self.controller.acquisition_in_progress():
                self.controller.clear_acquisition()
                self.controller.start_acquisition()
            #Then start the acquisition
            self.callback_signal.emit()  # will trigger the wait for acquisition

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [str(e), "log"]))

    def emit_data(self):
        """ Function used to emit data obtained by callback.

        Parameter
        ---------
        status: bool
            If True a frame is available, If False, a Timeout occured while waiting for the frame

        See Also
        --------
        daq_utils.ThreadCommand
        """
        try:
            # Get  data from buffer
            frame = self.controller.read_newest_image()
            # Emit the frame.
            if frame is not None:       # happens for last frame when stopping camera
                if self.settings['output_color'] == 'RGB':
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2RGB)
                    self.data_grabed_signal.emit([DataFromPlugins(name='Thorlabs Camera',
                                                                  data=[np.squeeze(rgb_image[..., ind]) for ind in
                                                                        range(3)],
                                                                  dim=self.data_shape,
                                                                  labels=[f'ThorCam_{self.data_shape}'])])
                else:
                    if 'monochrome' in self.settings['sensor'].lower():
                        self.data_grabed_signal.emit([DataFromPlugins(name='Thorlabs Camera',
                                                                      data=[np.squeeze(frame)],
                                                                      dim=self.data_shape,
                                                                      labels=[f'ThorCam_{self.data_shape}'])])
                    else:
                        grey_image = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2GRAY)
                        self.data_grabed_signal.emit([DataFromPlugins(name='Thorlabs Camera',
                                                                      data=[np.squeeze(grey_image)],
                                                                      dim=self.data_shape,
                                                                      labels=[f'ThorCam_{self.data_shape}'])])

            if self.settings.child('timing_opts', 'fps_on').value():
                self.update_fps()

            # To make sure that timed events are executed in continuous grab mode
            QtWidgets.QApplication.processEvents()

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))

    def update_fps(self):
        current_tick = perf_counter()
        frame_time = current_tick-self.last_tick

        if self.last_tick != 0.0 and frame_time != 0.0:
            # We don't update FPS for the first frame, and we also avoid divisions by zero

            if self.fps == 0.0:
                self.fps = 1 / frame_time
            else:
                # If we already have an FPS calculated, we smooth its evolution
                self.fps = 0.9 * self.fps + 0.1 / frame_time

        self.last_tick = current_tick

        # Update reading
        self.settings.child('timing_opts', 'fps').setValue(round(self.fps, 1))

    def close(self):
        """
        Terminate the communication protocol
        """
        # Terminate the communication
        self.controller.close()
        self.controller = None  # Garbage collect the controller
        self.status.initialized = False
        self.status.controller = None
        self.status.info = ""

    def stop(self):
        """Stop the acquisition."""
        self.controller.clear_acquisition()
        return ''


class ThorlabsCallback(QtCore.QObject):
    """Callback object """
    data_sig = QtCore.Signal()

    def __init__(self, wait_fn):
        super().__init__()
        # Set the wait function
        self.wait_fn = wait_fn

    def wait_for_acquisition(self):
        try:
            new_data = self.wait_fn()
            if new_data is not False:  # will be returned if the main thread called CancelWait
                self.data_sig.emit()
        except Thorlabs.ThorlabsTimeoutError:
            pass


if __name__ == '__main__':
    main(__file__, init=False)
