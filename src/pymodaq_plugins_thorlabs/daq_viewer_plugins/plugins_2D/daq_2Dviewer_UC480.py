
from pymodaq.control_modules.viewer_utility_classes import comon_parameters, main

from pylablib.devices import uc480

from pymodaq_plugins_thorlabs.hardware.camera_base import CameraBase, cam_params


class DAQ_2DViewer_UC480(CameraBase):
    """
    Plugin for either Thorlabs cameras uc480type or IDS µeye.

    This is the interface used in multiple cameras, including many simple Thorlabs and IDS cameras. It has been tested with IDS SC2592R12M and Thorlabs DCC1545M.

    Essentially identical interface is available under two different implementations:
    either as Thorlabs uc480 or as IDS uEye. Both of these seem to cover exactly the same cameras,
    both are freely available from the manufacturers, and both implement exactly the same functionality.
    However, these interfaces are not interchangeable, and each camera will only interact with one of
    them depending on which driver it happens to use (usually based on which of the software packages
    was installed last). Hence, if you have both ThorCam and IDS Software Suite installed, you would
    need to check both interfaces. Normally, the interface should correspond to the software which can
    connect to the camera (either ThorCam or uEye Cockpit).

    Building on pylablib driver, information about it can be found here:
    https://pylablib.readthedocs.io/en/latest/devices/uc480.html#cameras-uc480

    The plugin provides binning functionality as well as ROI (region of interest) selection, which are on handled the hardware side.
    To use ROIs, click on "Show/Hide ROI selection area" in the viewer panel (icon with dashed rectangle).
    Position the rectangle as you wish, either with mouse or by entering coordinates, then click "Update ROI" button.

    The "Clear ROI+Bin" button resets to default cameras parameters: no binning and full frame.
    """
    serial_numbers = [cam_info.serial_number for cam_info in uc480.list_cameras()]
    serial_params = [{'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serial_numbers}]

    params = comon_parameters + serial_params + cam_params

    def ini_attributes(self):
        super().ini_attributes()
        self.controller: uc480.UC480Camera = None

    def ini_detector_custom(self, controller=None):
        # Initialize camera class
        if not self.settings.child('serial_number').value() == '':
            if self.is_master:
                self.controller = uc480.UC480Camera(
                    dev_id=uc480.UC480Camera.find_by_serial(self.settings.child('serial_number').value()))
            else:
                self.controller = controller
        else:
            raise Exception('No compatible Thorlabs UC480 camera was found.')


if __name__ == '__main__':
    main(__file__, init=False)
