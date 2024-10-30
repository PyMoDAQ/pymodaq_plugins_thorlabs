"""
Description:
------------

python wrapper around the TLPM.dll from Thorlabs
it supports the following Thorlabs power meters and appropriate sensors and can administer them in parallel.
· PM101x (PM101, PM101A, PM101R, PM101U)
· PM102x (PM102, PM102A, PM102U)
· PM103x (PM103, PM103A, PM103U)
· PM100USB
· PM16-Series
· PM160 1)
· PM160T 1)
· PM160T-HP 1)
· PM400
· PM100A
· PM100D
· PM200

Installation:
-------------

* Download the Optical Power Monitor software from thorlabs website:
  https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM
* after installation, the dll driver and TLPM.py wrapper will be installed in the
  C:\ProgramFiles\IVI Foundation\VISA\Win64\ or  C:\ProgramFiles (x86)\IVI Foundation\VISA\WinNT\
  under the environment variable VXIPNPPATH or VXIPNPPATH64
  >>>import os
  >>>os.environ['VXIPNPPATH']
"""

import os
import sys
import importlib
from pathlib import Path
import ctypes
import functools

from pymodaq.utils import daq_utils as utils
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))
if utils.is_64bits():
    path_dll = str(Path(os.environ['VXIPNPPATH64']).joinpath('Win64', 'Bin'))
else:
    path_dll = str(Path(os.environ['VXIPNPPATH']).joinpath('WinNT', 'Bin'))
os.add_dll_directory(path_dll)


def tlpm_path(tlpm: Path):
    return Path(os.environ['VXIPNPPATH']).joinpath('WinNT', 'TLPM', tlpm, 'Python')


module_error = True
for example_str in ['Example', 'Examples']:
    try:
        path_python_wrapper = tlpm_path(example_str)
        sys.path.insert(0, str(path_python_wrapper))
        import TLPM
        module_error = False
        break
    except ModuleNotFoundError as e:
        pass
if module_error:
    error = f"The *TLPM.py* python wrapper of thorlabs TLPM dll could not be located on your system. Check if present"\
            f" in one of these path:\n"\
            f"{tlpm_path('Example')}\n"\
            f"{tlpm_path('Examples')}"
    raise ModuleNotFoundError(error)

def error_handling(default_arg=None):
    """decorator around TLPM functions to handle return if errors"""
    def error_management(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                ret = func(*args, **kwargs)
                return ret
            except Exception as e:
                logger.debug(f'The function {func.__name__} returned the error: {e}')
                return default_arg
        return wrapper
    return error_management


class DeviceInfo:
    def __init__(self, model_name='', serial_number='', manufacturer='', is_available=False):
        self.model_name = model_name
        self.serial_number = serial_number
        self.manufacturer = manufacturer
        self.is_available = is_available

    def __repr__(self):
        return f'Model: {self.model_name} / SN: {self.serial_number} by {self.manufacturer} is'\
               f' {"" if self.is_available else "not"} available'


class GetInfos:
    def __init__(self, tlpm=None):
        if tlpm is None:
            tlpm = TLPM.TLPM()
        self._tlpm = tlpm
        self._Ndevices = 0

    @error_handling(0)
    def get_connected_ressources_number(self):
        deviceCount = ctypes.c_uint32()
        self._tlpm.findRsrc(ctypes.byref(deviceCount))
        self._Ndevices = deviceCount.value
        return self._Ndevices

    def get_devices_name(self):
        self.get_connected_ressources_number()
        names = []
        resource_name = ctypes.create_string_buffer(1024)
        for ind in range(self._Ndevices):
            self._tlpm.getRsrcName(ctypes.c_int(ind), resource_name)
            names.append(resource_name.value.decode())
        return names

    @error_handling(DeviceInfo())
    def get_devices_info(self, index: int):
        self.get_connected_ressources_number()
        if index >= self._Ndevices:
            return DeviceInfo()
        modelName = ctypes.create_string_buffer(1024)
        serialNumber = ctypes.create_string_buffer(1024)
        manufacturer = ctypes.create_string_buffer(1024)
        is_available = ctypes.c_int16()
        self._tlpm.getRsrcInfo(index, modelName, serialNumber, manufacturer, ctypes.byref(is_available))
        return DeviceInfo(modelName.value.decode(), serialNumber.value.decode(),
                          manufacturer.value.decode(), bool(is_available.value))


infos = GetInfos()
Ndevices = infos.get_connected_ressources_number()
DEVICE_NAMES = infos.get_devices_name()


class CustomTLPM:
    def __init__(self, index=None):
        super().__init__()
        self._index = index
        self._tlpm = TLPM.TLPM()
        self.infos = GetInfos(self._tlpm)

    def __enter__(self):
        device_name = self.infos.get_devices_name()[self._index]
        self.open(device_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open_by_index(self, index=None):
        if index is not None:
            self._index = index
        device_name = self.infos.get_devices_name()[self._index]
        self.open(device_name)

    @error_handling(False)
    def open(self, resource_name: str, id_query=True, reset=True):
        resource = ctypes.create_string_buffer(1024)
        resource.value = resource_name.encode()
        id_query = ctypes.c_bool(id_query)
        reset = ctypes.c_bool(reset)
        self._tlpm.open(resource, id_query, reset)
        return True

    @error_handling()
    def close(self):
        self._tlpm.close()

    @error_handling('')
    def get_calibration(self):
        message = ctypes.create_string_buffer(1024)
        self._tlpm.getCalibrationMsg(message)
        return message.value.decode()

    @error_handling(0.)
    def get_power(self):
        power = ctypes.c_double()
        self._tlpm.measPower(ctypes.byref(power))
        return power.value

    @property
    @error_handling((500, 800))
    def wavelength_range(self):
        wavelength_min = ctypes.c_double()
        wavelength_max = ctypes.c_double()

        self._tlpm.getWavelength(TLPM.TLPM_ATTR_MIN_VAL, ctypes.byref(wavelength_min))
        self._tlpm.getWavelength(TLPM.TLPM_ATTR_MAX_VAL, ctypes.byref(wavelength_max))
        return wavelength_min.value, wavelength_max.value

    @property
    @error_handling(-1)
    def wavelength(self):
        wavelength = ctypes.c_double()
        self._tlpm.getWavelength(TLPM.TLPM_ATTR_SET_VAL, ctypes.byref(wavelength))
        return wavelength.value

    @wavelength.setter
    @error_handling()
    def wavelength(self, wavelength: float):
        wavelength = ctypes.c_double(wavelength)
        self._tlpm.setWavelength(wavelength)


if __name__ == '__main__':
    from time import sleep
    print(Ndevices)
    print(DEVICE_NAMES)

    with CustomTLPM(0) as tlpm:
        print(tlpm.wavelength)
        tlpm.wavelength = 532.
        sleep(1)
        print(tlpm.wavelength)
        print(tlpm.get_power())


