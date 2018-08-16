#!/usr/bin/env python3
import sys
from PyQt5 import QtWidgets, QtCore
from bgui import mainwin


def main(app):
    # create window and place it to the screen center
    wind = mainwin.MainWindow('./test_db/test.db')
    wind.resize(800, 600)
    wind.setGeometry(QtWidgets.QStyle.alignedRect(
        QtCore.Qt.LeftToRight,
        QtCore.Qt.AlignCenter,
        wind.size(),
        app.desktop().availableGeometry()))
    wind.show()

    # start gui loop
    sys.exit(QtWidgets.qApp.exec_())


if __name__ == '__main__':
    # # initialize qt application here to prevent
    # # segmentation fault on exit
    qApp = QtWidgets.QApplication(sys.argv)
    main(qApp)
