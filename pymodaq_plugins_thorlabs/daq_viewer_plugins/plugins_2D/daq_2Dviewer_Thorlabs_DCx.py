import numpy as np
from easydict import EasyDict as edict
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo, DataFromPlugins, Axis
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base, comon_parameters
from instrumental import instrument, list_instruments

class DAQ_2DViewer_Thorlabs_DCx(DAQ_Viewer_base):
    """This plugin use the instrumental library:
        https://instrumental-lib.readthedocs.io/en/stable/

        The class we use is defined here:
        https://github.com/mabuchilab/Instrumental/blob/master/instrumental/drivers/
        cameras/uc480.py
    """
    params = comon_parameters + []

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

        self.x_axis = None
        self.y_axis = None

        self.controller = None

    def commit_settings(self, param):
        """
        """

    def ini_detector(self, controller=None):
        """Detector communication initialization
        Parameters
        ----------
        controller: (object) custom object of a PyMoDAQ plugin (Slave case).
            None if only one detector by controller (Master case)
        Returns
        -------
        self.status (edict): with initialization status: three fields:
            * info (str)
            * controller (object) initialized controller
            * initialized: (bool): False if initialization failed otherwise True
        """

        try:
            self.status.update(edict(initialized=False, info="", x_axis=None,
                                     y_axis=None, controller=None))
            if self.settings.child('controller_status').value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while'
                                    'this detector is a slave one')
                else:
                    self.controller = controller
            else:
                paramsets = list_instruments()
                self.controller = instrument(paramsets[0])
                # for now we suppose that only one camera is plugged

            image = self.controller.grab_image()

            data_x_axis = image[0, :]
            self.x_axis = Axis(data=data_x_axis, label='', units='')
            self.emit_x_axis()

            data_y_axis = image[:, 0]
            self.y_axis = Axis(data=data_y_axis, label='', units='')
            self.emit_y_axis()

            # initialize viewers pannel with the future type of data
            # self.data_grabed_signal_temp.emit([
            #     DataFromPlugins(name='Mock1', data=["2D numpy array"], dim='Data2D',
            #                     labels=['dat0'], x_axis=self.x_axis, y_axis=self.y_axis)
            # ])

            self.status.info = "Whatever info you want to log"
            self.status.initialized = True
            self.status.controller = self.controller
            return self.status

        except Exception as e:
            self.emit_status(
                ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def close(self):
        """
        Terminate the communication protocol
        """
        self.controller.close()

    def grab_data(self, Naverage=1, **kwargs):
        """
        Parameters
        ----------
        Naverage: (int) Number of hardware averaging
        kwargs: (dict) of others optionals arguments
        """

        data_tot = [np.array(self.controller.grab_image())]
        self.data_grabed_signal.emit([DataFromPlugins(name='Mock1', data=data_tot,
                                                      dim='Data2D', labels=['dat0'])])

    def stop(self):

        self.controller.stop_live_video()
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

        return ''


def main():
    """
    this method start a DAQ_Viewer object with this defined plugin as detector
    Returns
    -------
    """
    import sys
    from PyQt5 import QtWidgets
    from pymodaq.daq_utils.gui_utils import DockArea
    from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
    from pathlib import Path

    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Viewer')
    detector = Path(__file__).stem[13:]
    det_type = f'DAQ{Path(__file__).stem[4:6].upper()}'
    prog = DAQ_Viewer(area, title="Testing", DAQ_type=det_type)
    win.show()
    prog.detector = detector
    prog.init_det()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()