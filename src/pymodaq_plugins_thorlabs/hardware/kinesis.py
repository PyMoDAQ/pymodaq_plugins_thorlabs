import clr
import sys
from typing import Dict

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
clr.AddReference("Thorlabs.MotionControl.Benchtop.BrushlessMotorCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.PiezoCLI")

import Thorlabs.MotionControl.FilterFlipperCLI as FilterFlipper
import Thorlabs.MotionControl.IntegratedStepperMotorsCLI as Integrated
import Thorlabs.MotionControl.DeviceManagerCLI as Device
import Thorlabs.MotionControl.GenericMotorCLI as Generic
import Thorlabs.MotionControl.Benchtop.BrushlessMotorCLI as BrushlessMotorCLI
import Thorlabs.MotionControl.KCube.PiezoCLI as KCubePiezo

Device.DeviceManagerCLI.BuildDeviceList()
serialnumbers_integrated_stepper = [str(ser) for ser in
                                    Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)]
serialnumbers_flipper = [str(ser) for ser in
                         Device.DeviceManagerCLI.GetDeviceList(FilterFlipper.FilterFlipper.DevicePrefix)]
serialnumbers_brushless = [str(ser) for ser in
                           Device.DeviceManagerCLI.GetDeviceList(BrushlessMotorCLI.BenchtopBrushlessMotor.DevicePrefix)]
serialnumbers_piezo = [str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(KCubePiezo.KCubePiezo.DevicePrefix)]


class Kinesis:
    default_units = ''

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
    def serial_number(self) -> str:
        return self._device.GetDeviceInfo().SerialNumber

    @property
    def backlash(self):
        return Decimal.ToDouble(self._device.GetBacklash())

    @backlash.setter
    def backlash(self, backlash: float):
        self._device.SetBacklash(Decimal(backlash))

    def stop(self):
        self._device.Stop(0)

    def move_done_callback(self, val: int):
        print('move done')

    def move_abs(self, position: float, callback=None, **kwargs):
        if callback is not None:
            callback = Action[UInt64](callback)
        else:
            callback = 0
        self._device.MoveTo(Decimal(position), callback)

    def move_rel(self, position: float, callback=None, **kwargs):
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

    @property
    def is_homed(self) -> bool:
        return self._device.Status.IsHomed

    @property
    def is_moving(self) -> bool:
        return self._device.Status.IsInMotion

    @property
    def is_homing(self) -> bool:
        return self._device.Status.IsHoming

    def get_position(self, **kwargs):
        raise NotImplementedError

    def get_target_position(self, *args, **kwargs) -> float:
        return Decimal.ToDouble(self._device.Position)

    def get_units(self, *args, **kwargs) -> str:
        """ Get the stage units from the controller

        """
        try:
            units = self._device.get_UnitConverter().RealUnits
        except Exception:
            units = self.default_units
        return units


class IntegratedStepper(Kinesis):
    """ Specific Kinesis class for Integrated Stepper motor"""

    default_units = '°'

    def __init__(self):
        super().__init__()
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

    def get_position(self, **kwargs):
        return Decimal.ToDouble(self._device.ContinuousRotationPosition)

    def get_units(self, *args, **kwargs) -> str:
        return super().get_units()


class BrushlessMotorChannel(Kinesis):
    properties = ['MaxPosition', 'MinPosition',
                  'MaxAcceleration', 'MaxDecceleration',
                  'MaxVelocity']

    default_units = 'mm'

    def __init__(self, controller_device: BrushlessMotorCLI.BenchtopBrushlessMotor,
                 channel_index=1):
        super().__init__()
        self._controller = controller_device
        self._device: BrushlessMotorCLI.BrushlessMotorChannel = None
        self._channel_index = channel_index
        self.motorConfiguration = None

    def get_property(self, prop: str):
        if prop in self.properties:
            return Decimal.ToDouble(getattr(self._device.GetStageAxisParams(), prop))

    def set_property(self, prop: str, value: float):
        if prop in self.properties:
            return setattr(self._device.GetStageAxisParams(), prop, Decimal(value))

    def connect(self, *args, **kwargs):
        self._device: BrushlessMotorCLI.BrushlessMotorChannel = (
            self._controller.GetChannel(self._channel_index))
        self._device.WaitForSettingsInitialized(5000)

        if not (self._device.IsSettingsInitialized()):
            raise (Exception("no Stage Connected"))
        else:
            self.motorConfiguration = self._device.LoadMotorConfiguration(self._device.DeviceID)
        self._device.StartPolling(250)
        self._device.EnableDevice()

    def get_position(self) -> float:
        return Decimal.ToDouble(self._device.get_DevicePosition())


class BrushlessDCMotor(Kinesis):
    """ Specific Kinesis class for Brushless DC Motors"""
    n_channels = 3
    default_units = 'mm'

    def __init__(self):
        super().__init__()
        self._device: BrushlessMotorCLI.BenchtopBrushlessMotor = None
        self._channels: Dict[int, BrushlessMotorChannel] = {}
        self._current_channel_index = 1

    def connect(self, serial: int):
        if serial in serialnumbers_brushless:
            self._device = (
                BrushlessMotorCLI.BenchtopBrushlessMotor.CreateBenchtopBrushlessMotor(serial))
            self._device.Connect(serial)

    def init_channel(self, channel=1) -> BrushlessMotorChannel:
        self._channels[channel] = BrushlessMotorChannel(self._device, channel)
        self._channels[channel].connect()
        return self._channels[channel]

    def get_position(self, channel: int = 1) -> float:
        if channel not in self._channels:
            self.init_channel(channel)
        return self._channels[channel].get_position()

    def move_abs(self, position: float, callback=None, channel: int = 1):
        if channel not in self._channels:
            self.init_channel(channel)
        self._channels[channel].move_abs(position, callback)

    def close(self):
        for channel in self._channels.values():
            channel.close()
        self._device.Disconnect()

    def home(self, channel: int = 1, callback=None):
        if channel not in self._channels:
            self.init_channel(channel)
        self._channels[channel].home(callback)

    def is_homed(self, channel: int = 1) -> bool:
        if channel not in self._channels:
            self.init_channel(channel)
        return self._channels[channel].is_homed

    def stop(self, channel: int = 1):
        if channel not in self._channels:
            self.init_channel(channel)
        self._channels[channel].stop()

    def get_units(self, channel: int = 1) -> str:
        """ Get the stage units from the controller
        """
        if channel not in self._channels:
            self.init_channel(channel)
        return self._channels[channel].get_units()

    def get_target_position(self, channel: int = 1) -> float:
        if channel not in self._channels:
            self.init_channel(channel)
        return self._channels[channel].get_target_position()


class Flipper(Kinesis):
    """ Specific Kinesis class for Flipper"""

    default_units = ''

    def __init__(self):
        super().__init__()
        self._device: FilterFlipper.FilterFlipper = None

    def connect(self, serial: int):
        if serial in serialnumbers_flipper:
            self._device = FilterFlipper.FilterFlipper.CreateFilterFlipper(serial)
            super().connect(serial)
            if not (self._device.IsSettingsInitialized()):
                raise (Exception("no Stage Connected"))
        else:
            raise ValueError('Invalid Serial Number')

    def move_abs(self, position: float, callback=None, **kwargs):
        if int(position) == 1:
            position = 1
        else:
            position = 2
        self._device.SetPosition(UInt32(position), 0)

    def get_position(self, **kwargs):
        position = int(self._device.Position)
        if position == 2:
            position = 0
        else:
            position = 1
        return position


class Piezo(Kinesis):
    default_units = 'V'

    def __init__(self):
        self._device: KCubePiezo.KCubePiezo = None

    def connect(self, serial: int):
        if serial in serialnumbers_piezo:
            self._device = (
                KCubePiezo.KCubePiezo.CreateKCubePiezo(serial))
            self._device.Connect(serial)
            self._device.StartPolling(250)
            self._device.EnableDevice()
            self._device.GetPiezoConfiguration(serial)
        else:
            raise ValueError('Invalid Serial Number')

    def move_abs(self, position: float):
        self._device.SetOutputVoltage(Decimal(position))

    def home(self):
        self.move_abs(0.0)

    def get_position(self) -> float:
        return Decimal.ToDouble(self._device.GetOutputVoltage())

    def stop(self):
        pass

if __name__ == '__main__':
    controller = BrushlessDCMotor()
    controller.connect(serialnumbers_brushless[0])
    motor = controller.init_channel(1)
    print(motor.get_units())
    motor.home()
    print(f'homing: {motor.is_homing}')
    print(f'Moving: {motor.is_moving}')
    print(motor.get_target_position())

    motor.move_abs(87, motor.move_done_callback)
    print(f'homing: {motor.is_homing}')
    print(f'Moving: {motor.is_moving}')
    print(motor.get_target_position())

    controller.close()