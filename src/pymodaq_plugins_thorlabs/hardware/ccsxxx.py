# This code is reproduced from https://github.com/Thorlabs/Light_Analysis_Examples/blob/main/Python/Thorlabs%20CCS%20Spectrometers/CCS%20using%20ctypes%20-%20Python%203.py

# import python libraries
import ctypes

# DK load dll file
dll_path = r"C:\Program Files\IVI Foundation\VISA\Win64\Bin\TLCCS_64.dll"
ccs_dll = ctypes.CDLL(dll_path)
resource_name = " "


class CCSXXX:
    def __init__(self,dll_path,resource_name):
            self.dll_path = dll_path
            self.resource_name = resource_name.encode('')
            self.handle = ctypes.c_int()
            self.ccs_dll = ctypes.CDLL(dll_path)
            self.connect_device()
#initialization of spectrometer#
    def connect_device(self):
        init_func = self.ccs_dll.TLCCS_init
        init_func.restype = ctypes.c_int
        init_func.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]

        id_query = 1
        status = init_func(self.resource_name, id_query, ctypes.byref(self.handle))
        if status != 0:
            raise Exception(f"Error initializing spectrometer: {status}")
    #def close
       def close_device(self):
            close_func = self.ccs_dll.TLCCS_close
            close_func.restype = ctypes.c_int
            close_func.argtypes = [ctypes.c_int]

            status = close_func(self.handle)
            if status != 0:
                raise Exception(f"Error closing spectrometer: {status}")


        # set the integration time
     def set_integration_time(self, integration_time):
        set_integration_time_func = self.ccs_dll.TLCCS_setIntegrationTime
        set_integration_time_func.restype = ctypes.c_int
        set_integration_time_func.argtypes = [ctypes.c_int, ctypes.c_double]
        status = set_integration_time_func(self.handle, ctypes.c_double(integration_time))
        integration_time = 0.1  # in seconds
        self.set_integration_time(integration_time)
        if status != 0:
            raise Exception(f'Error setting integration time: {status})

    # start scanning i.e., expose the CCD via the monochrometer
    def start_scanning(self):
            start_scan_func = self.ccs_dll.TLCCS_startScan
            start_scan_func.restype = ctypes.c_int
            start_scan_func.argtypes = [ctypes.c_int]
            status = start_scan_func(self.handle)
            if status != 0:
                raise Exception(f"Error starting scan: {status}"


    # get the wavelength calibration coefficients
    def wavelength_calibration(self, calibration_points):
        set_calibration_func = self.ccs_dll.TLCCS_setWavelengthCalibration
        set_calibration_func.restype = ctypes.c_int
        set_calibration_func.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double), ctypes.c_int]
         num_points = len(calibration_points)
        calibration_array = (ctypes.c_double * num_points)(*calibration_points)

        status = set_calibration_func(self.handle, calibration_array, num_points)
        if status != 0:
            raise Exception(f"Error performing wavelength calibration: {status}")

    # get the data array i.e., a spectrum
    def acquire_spectrum(self):
            get_spectrum_func = self.ccs_dll.TLCCS_getSpectrum
            get_spectrum_func.restype = ctypes.c_int
            get_spectrum_func.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double), ctypes.c_int]
             spectrum = (ctypes.c_double * )()
            status = self.get_spectrum_func(self.handle, spectrum, len(spectrum))
            if status != 0:
                raise Exception(f"Error acquiring spectrum: {status}")
            return spectrum
