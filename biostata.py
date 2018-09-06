#!/usr/bin/env python3
import sys
from PyQt5 import QtWidgets
from bgui import mainwin
from prog import bopts


def main(app):
    # program options
    opts = bopts.BiostataOptions()
    opts.load()

    # create window
    wind = mainwin.MainWindow(opts)

    # place it to the screen center
    wind.show()

    # start gui loop
    QtWidgets.qApp.exec_()
    sys.exit()


if __name__ == '__main__':
    # initialize qt application here to prevent
    # segmentation fault on exit
    qApp = QtWidgets.QApplication(sys.argv)
    main(qApp)
