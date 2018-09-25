#!/usr/bin/env python3
import sys
from PyQt5 import QtWidgets
from bgui import mainwin
from prog import projroot, basic, bopts


def main(app):
    # logging
    if __debug__:
        basic.set_log_message('console')
        basic.set_ignore_exception(True)
    else:
        basic.set_log_message('file: ' + bopts.BiostataOptions.logfile())
        basic.set_ignore_exception(True)

    # create window
    mainwin.MainWindow(projroot.proj).show()

    # start gui loop
    QtWidgets.qApp.exec_()

    projroot.proj.finish()


if __name__ == '__main__':
    # initialize qt application here to prevent
    # segmentation fault on exit
    qApp = QtWidgets.QApplication(sys.argv)
    main(qApp)
    sys.exit()
