#!/usr/bin/env python3
import sys
from PyQt5 import QtWidgets
from bgui import mainwin
from prog import projroot, basic, bopts, command


def main(app):
    # logging
    if __debug__:
        basic.set_log_message('console')
        basic.set_ignore_exception(True)
    else:
        basic.set_log_message('file: ' + bopts.BiostataOptions.logfile())
        basic.set_ignore_exception(True)

    proj = projroot.ProjectDB()
    opts = bopts.BiostataOptions()
    opts.load()
    flow = command.CommandFlow()

    # create window
    mwin = mainwin.MainWindow(flow, proj, opts)
    mwin.show()

    # start gui loop
    QtWidgets.qApp.exec_()

    proj.finish()


if __name__ == '__main__':
    # initialize qt application here to prevent
    # segmentation fault on exit
    qApp = QtWidgets.QApplication(sys.argv)
    main(qApp)
    sys.exit()
