pymodaq_plugins_thorlabs (Thorlabs Instruments)
###############################################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_thorlabs.svg
   :target: https://pypi.org/project/pymodaq_plugins_thorlabs/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/PyMoDAQ/pymodaq_plugins_thorlabs/workflows/Upload%20Python%20Package/badge.svg
   :target: https://github.com/PyMoDAQ/pymodaq_plugins_thorlabs
   :alt: Publication Status

Set of PyMoDAQ plugins for instruments from Thorlabs (Kinesis K10CR1 (stepper rotation actuator), Kinesis Flipper,
Kinesis KSP100, Camera DCx, Scientific cameras, Powermeters using the TLPM library)


Authors
=======

* Sebastien J. Weber
* David Bresteau (david.bresteau@cea.fr)
* Nicolas Tappy (nicolas.tappy@epfl.ch)
* Romain Geneaux (romain.geneaux@cea.fr)

Instruments
===========

Below is the list of instruments included in this plugin

Actuators
+++++++++

* **Kinesis**: Kinesis serie (tested on K10CR1)
* **Kinesis_Flipper**: Kinesis serie Flipper
* **MFF101_pylablib**: Kinesis serie Flipper mount (thorlabs MFF101), similar to **Kinesis_FLipper** but using the pylablib control module.
* **PRM1Z8_pylablib**: DC servo motorized 360° rotation mount (Thorlabs PRM1Z8) using the pylablib control module. The Thorlabs APT software should be installed: https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=9019.

Viewer0D
++++++++

* **Kinesis_KPA101**: Kinesis serie (position sensitive photodetector)
* **TLPMPowermeter**: TLPM dll compatible series (PM101x, PM102x, PM103x, PM100USB, PM16-Series, PM160, PM400, PM100A, PM100D, PM200)
* **TLPMPowermeterInst**: TLPM dll compatible series (PM101x, PM102x, PM103x, PM100USB, PM16-Series, PM160, PM400, PM100A, PM100D, PM200)
  using the Instrumental-lib package (recommended)

Viewer2D
++++++++

* **DCx cameras**: Tested with DCC3240M. Works with Windows. Precise installation instructions can be found here:
  https://instrumental-lib.readthedocs.io/en/stable/uc480-cameras.html and in the plugin file.
* **Scientific cameras**: sCMOS camera series Zelux, Kiralux, Quantalux. Implemented using the pylablib control module.
  Required libraries are installed using the free `ThorCam <https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam>`__ software.
  The plugin assumes Thorcam is installed in default folder (see `details here <https://pylablib.readthedocs.io/en/stable/devices/Thorlabs_TLCamera.html>`__). Tested on Zelux camera on Windows.