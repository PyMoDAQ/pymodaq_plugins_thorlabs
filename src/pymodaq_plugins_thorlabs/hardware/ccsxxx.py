# This code is reproduced from https://github.com/Thorlabs/Light_Analysis_Examples/blob/main/Python/Thorlabs%20CCS%20Spectrometers/CCS%20using%20ctypes%20-%20Python%203.py

# import python libraries

# DK load dll file

class CCSXXX:
    def __init__(self):
        self._device = None

    def connect

    def close

    # set the integration time
    def jdj

    # start scanning i.e., expose the CCD via the monochrometer
    def yyz

    # get the wavelength calibration coefficients
    def xssa

    # get the data array i.e., a spectrum
    def xxx(self, xxx, yyy, zzz):
        spectrum = do_something
        return spectrum