import traceback
from PyQt5 import QtWidgets


def message_exc(parent=None, title="Error", text=None, e=None):
    dlg = QtWidgets.QMessageBox(parent)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dlg.setIcon(QtWidgets.QMessageBox.Warning)
    dlg.setWindowTitle(title)
    txt = ""
    if text is not None:
        txt = text.strip()
    if e is not None:
        if text is not None:
            txt = txt + ' ' + str(e)
        else:
            txt = str(e)
        traceback.print_exc()
        dlg.setDetailedText(traceback.format_exc())
    dlg.setText(txt)
    dlg.setDefaultButton(dlg.button(QtWidgets.QMessageBox.Ok))
    return dlg.exec_()
