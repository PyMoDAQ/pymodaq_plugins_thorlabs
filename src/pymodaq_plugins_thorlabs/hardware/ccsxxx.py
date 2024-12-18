import os
import ctypes
import numpy as np

dll_path = r"C:\Program Files\IVI Foundation\VISA\Win64\Bin"
os.chdir(dll_path)
lib = ctypes.cdll.LoadLibrary("TLCCS_64.dll")

class CCSXXX:
    def __init__(self, rsrc_name):
        self.rsrc_name = rsrc_name.encode('utf-8')
        self.ccs_handle = ctypes.c_int(0)

    def connect(self):
        # connect to the device using DLL's init function'
        self._device = lib.tlccs_init(self.rsrc_name, 1, 1, ctypes.byref(self.ccs_handle))
        if self._device != 0:
            raise Exception("Failed to initialize the device")

    def set_integration_time(self, integration_time):
        """

        Args:
            integration_time: in seconds

        Returns:

        """
        integration_time = ctypes.c_double(integration_time)
        status = lib.tlccs_setIntegrationTime(self.ccs_handle, integration_time)
        if status != 0:
            raise Exception(f"Error setting integration time: {status}")

    def start_scan(self):
        status = lib.tlccs_startScan(self.ccs_handle)
        if status != 0:
            raise Exception(f"Error starting scan: {status}")

    def get_wavelength_data(self):
        wavelengths = (ctypes.c_double * 3648)()
        status = lib.tlccs_getWavelengthData(self.ccs_handle, 0, ctypes.byref(wavelengths), ctypes.c_void_p(None), ctypes.c_void_p(None))
        if status != 0:
            raise Exception(f"Error getting wavelength data: {status}")
        wavelengths = np.array(list(wavelengths))
        return wavelengths

    def get_scan_data(self):
        data_array = (ctypes.c_double * 3648)()
        status = lib.tlccs_getScanData(self.ccs_handle, ctypes.byref(data_array))
        if status != 0:
            raise Exception(f"Error getting scan data: {status}")
        data_array = np.array(list(data_array))
        return data_array

    def close(self):
        lib.tlccs_close(self.ccs_handle)

    #  self.lib.tlccs_close(self.ccs_handle)  # when writing your own plugin replace this line

# Example usage
if __name__ == "__main__":
    spectrometer = CCSXXX('USB0::0x1313::0x8087::M00934802::RAW')
    spectrometer.load_library()
    spectrometer.connect()
    spectrometer.set_integration_time(10.0e-3)
    spectrometer.start_scan()
    wavelengths = spectrometer.get_wavelength_data()