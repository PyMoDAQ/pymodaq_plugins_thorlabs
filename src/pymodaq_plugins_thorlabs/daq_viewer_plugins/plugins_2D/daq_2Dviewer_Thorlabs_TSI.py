from pymodaq.control_modules.viewer_utility_classes import comon_parameters, main

from pylablib.devices import Thorlabs

from pymodaq_plugins_thorlabs.hardware.camera_base import CameraBase, cam_params


""" note:
If the package is not working, this may be due to the use by pylablib of the ftd2xx.dll from ftdi (converting usb to 
COM port) through the kind of deprecated https://github.com/ftd2xx/ftd2xx package. Anyway, this one cannot (in some
unknown circumstances) load the ftd2xx.dll from its location (could be 
C:/Windows/System32/DriverStore/FileRepository/ftdibus.inf_amd64_6d7e924c4fdd3111/amd64) Then take it and place it in 
C:/Windows/System32/ eventually renaming it as ftd2xx.dll (if it was the ftd2xx64.dll as you may be running on AMD64)
That should solve this particular issue encountered on some win10 computers
"""


class DAQ_2DViewer_Thorlabs_TSI(CameraBase):
    """
    Plugin for TSI SCMOS Thorlabs cameras



    Building on pylablib driver, information about it can be found here:
    https://pylablib.readthedocs.io/en/latest/devices/

    The plugin provides binning functionality as well as ROI (region of interest) selection, which are on handled the hardware side.
    To use ROIs, click on "Show/Hide ROI selection area" in the viewer panel (icon with dashed rectangle).
    Position the rectangle as you wish, either with mouse or by entering coordinates, then click "Update ROI" button.

    The "Clear ROI+Bin" button resets to default cameras parameters: no binning and full frame.
    """
    serial_numbers = Thorlabs.list_cameras_tlcam()
    serial_params = [{'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'limits': serial_numbers}]
    params = comon_parameters + serial_params + cam_params

    def ini_attributes(self):
        super().ini_attributes()
        self.controller: Thorlabs.ThorlabsTLCamera = None

    def ini_detector_custom(self, controller=None):
        # Initialize camera class
        if not self.settings.child('serial_number').value() == '':
            if self.is_master:
                self.controller = Thorlabs.ThorlabsTLCamera(self.settings.child('serial_number').value())
            else:
                self.controller = controller
        else:
            raise Exception('No compatible Thorlabs TSI camera was found.')


if __name__ == '__main__':
    main(__file__, init=False)
