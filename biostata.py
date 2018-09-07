#!/usr/bin/env python3
import sys
from PyQt5 import QtWidgets
from bgui import mainwin
from prog import projroot


def main(app):
    # program initialization
    b = projroot.ProjectDB()

    # create window
    mainwin.MainWindow(b).show()

    # start gui loop
    QtWidgets.qApp.exec_()

    b.finish()
    sys.exit()


if __name__ == '__main__':
    # initialize qt application here to prevent
    # segmentation fault on exit
    qApp = QtWidgets.QApplication(sys.argv)
    main(qApp)
