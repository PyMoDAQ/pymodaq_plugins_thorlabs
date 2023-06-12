import clr
import sys

from System import Decimal
from System import Action
from System import UInt64
from System import UInt32

kinesis_path = 'C:\\Program Files\\Thorlabs\\Kinesis'
sys.path.append(kinesis_path)

clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
clr.AddReference("Thorlabs.MotionControl.FilterFlipperCLI")

import Thorlabs.MotionControl.FilterFlipperCLI as FilterFlipper
import Thorlabs.MotionControl.IntegratedStepperMotorsCLI as Integrated
import Thorlabs.MotionControl.DeviceManagerCLI as Device
import Thorlabs.MotionControl.GenericMotorCLI as Generic


Device.DeviceManagerCLI.BuildDeviceList()
serialnumbers_integrated_stepper = [str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)]
serialnumbers_flipper = [str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(FilterFlipper.FilterFlipper.DevicePrefix)]


class Kinesis:

    def __init__(self):
        self._device = None

    def connect(self, serial: int):
        self._device.Connect(serial)
        self._device.WaitForSettingsInitialized(5000)
        self._device.StartPolling(250)

    def close(self):
        """
            close the current instance of Kinesis instrument.
        """
        self._device.StopPolling()
        self._device.Disconnect()
        self._device.Dispose()
        self._device = None

    @property
    def name(self) -> str:
        return self._device.GetDeviceInfo().Name

    @property
    def backlash(self):
        return Decimal.ToDouble(self._device.GetBacklash())

    @backlash.setter
    def backlash(self, backlash: float):
        self._device.SetBacklash(Decimal(backlash))

    def stop(self):
        self._device.Stop(0)

    def move_abs(self, position: float, callback=None):
        if callback is not None:
            callback = Action[UInt64](callback)
        else:
            callback = 0
        self._device.MoveTo(Decimal(position), callback)

    def move_rel(self, position: float, callback=None):
        if callback is not None:
            callback = Action[UInt64](callback)
        else:
            callback = 0
        self._device.MoveRelative(Generic.MotorDirection.Forward, Decimal(position), callback)

    def home(self, callback=None):
        if callback is not None:
            callback = Action[UInt64](callback)
        else:
            callback = 0
        self._device.Home(callback)

    def get_position(self):
        raise NotImplementedError


class IntegratedStepper(Kinesis):

    def __init__(self):
        self._device: Integrated.CageRotator = None

    def connect(self, serial: int):
        if serial in serialnumbers_integrated_stepper:
            self._device = Integrated.CageRotator.CreateCageRotator(serial)
            super().connect(serial)
            if not (self._device.IsSettingsInitialized()):
                raise (Exception("no Stage Connected"))
            else:
                self._device.LoadMotorConfiguration(serial)
        else:
            raise ValueError('Invalid Serial Number')

    def get_position(self):
        return Decimal.ToDouble(self._device.ContinuousRotationPosition)


class Flipper(Kinesis):
    def __init__(self):
        self._device: FilterFlipper.FilterFlipper = None

    def connect(self, serial: int):
        if serial in serialnumbers_flipper:
            self._device = FilterFlipper.FilterFlipper.CreateFilterFlipper(serial)
            super().connect(serial)
            if not (self._device.IsSettingsInitialized()):
                raise (Exception("no Stage Connected"))
        else:
            raise ValueError('Invalid Serial Number')

    def move_abs(self, position: float, callback=None):
        if int(position) == 1:
            position = 1
        else:
            position = 2
        self._device.SetPosition(UInt32(position), 0)

    def get_position(self):
        position = int(self._device.Position)
        if position == 2:
            position = 0
        else:
            position = 1
        return position
