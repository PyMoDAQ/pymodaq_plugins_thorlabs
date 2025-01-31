from pathlib import Path
from pymodaq_utils.logger import set_logger  # to be imported by other modules.
from pymodaq_utils.utils import get_version, PackageNotFoundError

from .utils import Config
config = Config()

try:
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'