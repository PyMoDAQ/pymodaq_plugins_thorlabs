pymodaq_plugins_thorlabs (Thorlabs Instruments)
###############################################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_thorlabs.svg
   :target: https://pypi.org/project/pymodaq_plugins_thorlabs/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/CEMES-CNRS/pymodaq_plugins_thorlabs/workflows/Upload%20Python%20Package/badge.svg
    :target: https://github.com/CEMES-CNRS/pymodaq_plugins_thorlabs

Set of PyMoDAQ plugins for instruments from Thorlabs (Kinesis K10CR1 (stepper rotation actuator), Kinesis Flipper,
Kinesis KSP100, Camera DCx, Powermeters using the TLPM library)


Authors
=======

* Sebastien J. Weber
* David Bresteau (david.bresteau@cea.fr)

Instruments
===========

Below is the list of instruments included in this plugin

Actuators
+++++++++

* **Kinesis**: Kinesis serie (tested on K10CR1)
* **Kinesis_Flipper**: Kinesis serie Flipper

Viewer0D
++++++++

* **Kinesis_KPA101**: Kinesis serie (position sensitive photodetector)
* **TLPMPowermeter**: TLPM dll compatible series (PM101x, PM102x, PM103x, PM100USB, PM16-Series, PM160, PM400, PM100A, PM100D, PM200)

Viewer2D
++++++++

* **DCx cameras**: Tested with DCC3240M. Works with Windows. Precise installation instructions can be found here:
  https://instrumental-lib.readthedocs.io/en/stable/uc480-cameras.html and in the plugin file.


