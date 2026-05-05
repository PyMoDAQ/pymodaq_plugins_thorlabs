import cv2
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
try:
    from pymodaq_gui.plotting.items.roi import RoiInfo  # pymodaq > 5.1.x
except ImportError:
    from pymodaq_gui.plotting.utils.plot_utils import RoiInfo

from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main

from qtpy import QtWidgets, QtCore
import numpy as np
from time import perf_counter


cam_params = [
    {'title': 'Camera name:', 'name': 'camera_name', 'type': 'str', 'value': '', 'readonly': True},
    {'title': 'Sensor type:', 'name': 'sensor', 'type': 'list', 'limits': ['Monochrome', 'Bayer']},
    {'title': 'Ouput Color:', 'name': 'output_color', 'type': 'list', 'limits': ['RGB', 'MonoChrome']},
    {'title': 'ROI', 'name': 'roi', 'type': 'group', 'children': [
        {'title': 'Update ROI from Viewer', 'name': 'update_roi', 'type': 'led', 'value': False},
        {'title': 'Apply ROI', 'name': 'apply_roi', 'type': 'led', 'value': False},
        {'title': 'Clear ROI+Bin', 'name': 'clear_roi', 'type': 'bool_push', 'value': False},
        {'title': 'ROI:', 'name': 'roi_slices', 'type': 'str', 'value': ''},
        {'title': 'X binning', 'name': 'x_binning', 'type': 'int', 'value': 1},
        {'title': 'Y binning', 'name': 'y_binning', 'type': 'int', 'value': 1},
    ], },
    {'title': 'Image width', 'name': 'hdet', 'type': 'int', 'value': 1, 'readonly': True},
    {'title': 'Image height', 'name': 'vdet', 'type': 'int', 'value': 1, 'readonly': True},
    {'title': 'Timing', 'name': 'timing_opts', 'type': 'group', 'children':
        [{'title': 'Exposure Time (ms)', 'name': 'exposure_time', 'type': 'int', 'value': 1},
         {'title': 'Compute FPS', 'name': 'fps_on', 'type': 'bool', 'value': True},
         {'title': 'FPS', 'name': 'fps', 'type': 'float', 'value': 0.0, 'readonly': True}]
     },
    {'title': 'Buffer', 'name': 'buffer', 'type': 'group', 'children': [
        {'title': 'Size:', 'name': 'size', 'type': 'int', 'value': 10},
        {'title': 'mode:', 'name': 'mode', 'type': 'list', 'value': 'now',
         'limits': ['now', 'lastread', 'lastwait', 'start']},
    ]},
]


class CameraBase(DAQ_Viewer_base):
    """
    Base implementation for Camera using pylablib framework. Works for TSI and uc480 thorlabs camera
    """
    serial_numbers = []

    serial_params = [{'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serial_numbers}]

    params = comon_parameters + serial_params + cam_params

    callback_signal = QtCore.Signal(bool)
    live_mode_available = True

    def ini_attributes(self):
        self.controller = None
        self.callback_thread: QtCore.QThread = None

        self.x_axis: Axis = None
        self.y_axis: Axis = None

        self.roi_select_info: RoiInfo = None

        self.last_tick = 0.0  # time counter used to compute FPS
        self.fps = 0.0

        self.data_shape: str = ''


    def roi_select(self, roi_info: RoiInfo, ind_viewer: int = 0):
        """ Automatically called when a user use the RoiSelect ROi from a 2D viewer"""
        self.roi_select_info = roi_info
        self.roi_select_viewer_index = ind_viewer

        if self.settings['roi', 'update_roi']:
            self.settings['roi', 'roi_slices'] = str(roi_info.to_slices())
            if self.settings['roi', 'apply_roi']:
                self.apply_roi()

    def apply_roi(self):
        roi_info = RoiInfo.from_slices(eval(self.settings['roi', 'roi_slices']))
        new_roi = (roi_info.origin[1], roi_info.size[1], self.settings['roi', 'x_binning'],
                   roi_info.origin[0], roi_info.size[0], self.settings['roi', 'y_binning'])
        self.update_rois(new_roi)

    def compute_axes(self):
        (hstart, hend, vstart, vend, hbin, vbin) = self.controller.get_roi()
        slices = [slice(vstart, vend, vbin), slice(hstart, hend, hbin)]
        self.settings.child('roi', 'roi_slices').setValue(str(slices))
        roi_info = RoiInfo.from_slices(slices)

        self.x_axis = Axis('x_axis', offset=roi_info.origin[1],
                           scaling=self.settings['roi', 'x_binning'],
                           size=int(roi_info.size[1]),
                           index=1)
        self.y_axis = Axis('y_axis', offset=roi_info.origin[0],
                           scaling=self.settings['roi', 'y_binning'],
                           size=int(roi_info.size[0]),
                           index=0)

    def clear_roi(self):
        wdet, hdet = self.controller.get_detector_size()
        self.settings.child('roi', 'x_binning').setValue(1)
        self.settings.child('roi', 'y_binning').setValue(1)

        new_roi = (0, wdet, 1, 0, hdet, 1)
        self.update_rois(new_roi)

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
            self.compute_axes()

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

        if param.name() == "apply_roi":
            if param.value():   # Switching on ROI
                self.apply_roi()
            else:
                self.clear_roi()

        if param.name() in ['x_binning', 'y_binning']:
            # We handle ROI and binning separately for clarity
            (x0, w, y0, h, *_) = self.controller.get_roi()  # Get current ROI
            xbin = self.settings['roi', 'x_binning']
            ybin = self.settings['roi', 'y_binning']
            new_roi = (x0, w, xbin, y0, h, ybin)
            self.update_rois(new_roi)

        if param.name() == "clear_roi":
            if param.value():   # Switching on ROI
                self.clear_roi()
                param.setValue(False)

    def ini_detector_custom(self, controller=None):
        raise NotImplementedError

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
        self.ini_detector_custom(controller)

        self.get_device_info()
        self.get_set_color()
        self.get_set_main_parameters()
        self.setup_callback_thread()

        info = "Initialized camera"
        initialized = True
        return info, initialized

    def get_device_info(self):

        device_info = self.controller.get_device_info()

        # Get camera name/model
        if hasattr(device_info, 'name'):
            self.settings.child('camera_name').setValue(device_info.name)
        elif hasattr(device_info, 'model'):
            self.settings.child('camera_name').setValue(device_info.model)

    def get_set_color(self):
        if 'monochrome' in self.settings['sensor'].lower():
            self.settings.child('output_color').setValue('MonoChrome')
            self.settings.child('output_color').setOpts(visible=False)

    def get_set_main_parameters(self):
        # Set exposure time
        self.controller.set_exposure(self.settings['timing_opts', 'exposure_time']/1000)

        # FPS visibility
        self.settings.child('timing_opts', 'fps').setOpts(visible=self.settings['timing_opts', 'fps_on'])

        # get roi limits
        self.controller.get_roi_limits()

        # Update image parameters
        (hstart, hend, vstart, vend, hbin, vbin) = self.controller.get_roi()
        height, width = self.controller.get_data_dimensions()
        self.settings.child('roi', 'x_binning').setValue(hbin)
        self.settings.child('roi', 'y_binning').setValue(vbin)
        self.settings.child('hdet').setValue(width)
        self.settings.child('vdet').setValue(height)
        slices = [slice(vstart, vend, vbin), slice(hstart, hend, hbin)]
        self.settings.child('roi', 'roi_slices').setValue(str(slices))
        self.compute_axes()

    def setup_callback_thread(self):
        # Way to define a wait function with arguments
        wait_func = lambda: self.controller.wait_for_frame(since=self.settings['buffer', 'mode'],
                                                           nframes=1, timeout=20.0)
        callback = ThorlabsCallback(wait_func)
        self.settings.child('buffer', 'mode').setReadonly(True)


        self.callback_thread = QtCore.QThread()  # creation of a Qt5 thread
        callback.moveToThread(self.callback_thread)  # callback object will live within this thread
        callback.data_sig.connect(
            self.emit_data)  # when the wait for acquisition returns (with data taken), emit_data will be fired

        self.callback_signal.connect(callback.set_do_grab)
        self.callback_thread.callback = callback
        self.callback_thread.start()

        self._prepare_view()


    def _prepare_view(self):
        """Preparing a data viewer by emitting temporary data. Typically, needs to be called whenever the
        ROIs are changed"""

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

    def grab_data(self, Naverage=1, **kwargs):
        """
        Grabs the data. ASynchronous method (kinda).
        ----------
        Naverage: (int) Number of averaging
        kwargs: (dict) of others optionals arguments
        """
        try:
            # Warning, acquisition_in_progress returns 1,0 and not a real bool
            if not kwargs.get('live', False):
                self.emit_data(self.controller.snap())
            else:
                if not self.controller.acquisition_in_progress():
                    self.controller.clear_acquisition()
                    self.controller.start_acquisition(nframes=self.settings['buffer', 'size'])
                #Then start the acquisition
                self.callback_signal.emit(True)  # will trigger the wait for acquisition

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [str(e), "log"]))

    def emit_data(self, frame: np.ndarray=None):
        """ Function used to emit data obtained by callback.

        Parameter
        ---------
        status: bool
            If True a frame is available, If False, a Timeout occurred while waiting for the frame

        See Also
        --------
        daq_utils.ThreadCommand
        """
        try:
            # Get  data from buffer
            if frame is None:
                frame = self.controller.read_newest_image()
            # Emit the frame.
            if frame is not None:       # happens for last frame when stopping camera
                if self.settings['output_color'] == 'RGB':
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2RGB)
                    data_arrays = [np.atleast_1d(rgb_image[..., ind]) for ind in range(3)]
                else:
                    if 'monochrome' in self.settings['sensor'].lower():
                        data_arrays = [np.atleast_1d(frame)]
                    else:
                        data_arrays = [np.atleast_1d(cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2GRAY))]

                self.data_grabed_signal.emit([DataFromPlugins(name='Thorlabs Camera',
                                                              data=data_arrays,
                                                              dim=self.data_shape,
                                                              labels=[f'ThorCam_{self.data_shape}'],
                                                              axes=[self.x_axis, self.y_axis])])
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

        self.stop()
        if self.callback_thread is not None:
            self.callback_thread.quit()
            self.callback_thread.wait()

        self.controller.close()
        self.settings.child('buffer', 'mode').setReadonly(False)

    def stop(self):
        """Stop the acquisition."""
        self.callback_signal.emit(False)
        QtWidgets.QApplication.processEvents()

        self.controller.clear_acquisition()
        return ''


class ThorlabsCallback(QtCore.QObject):
    """Callback object """
    data_sig = QtCore.Signal()

    def __init__(self, wait_fn):
        super().__init__()
        # Set the wait function
        self.wait_fn = wait_fn
        self.do_grab = True

    def set_do_grab(self, do_grab=True):
        self.do_grab = do_grab
        if do_grab:
            self.wait_for_acquisition()

    def wait_for_acquisition(self):
        while self.do_grab:
            try:
                new_data = self.wait_fn()
                if new_data is not False:  # will be returned if the main thread called CancelWait
                    self.data_sig.emit()
            except Exception as e:
                pass
            QtWidgets.QApplication.processEvents()



