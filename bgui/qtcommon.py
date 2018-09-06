import traceback
from PyQt5 import QtWidgets, QtCore


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


_window_positions = {}
_window_classes = {}


def hold_position(cls):
    global _window_positions, _window_classes

    nm = '.'.join([cls.__module__, cls.__qualname__])

    class Ret(cls):
        _internal_name = nm

        def __init__(self, *args, **kwargs):
            cls.__init__(self, *args, **kwargs)
            ps = _window_positions[self._internal_name]
            try:
                self.resize(ps['W'], ps['H'])
            except:
                pass
            try:
                self.move(ps['X'], ps['Y'])
            except:
                pass
            try:
                self.setWindowState(QtCore.Qt.WindowState(ps['STATE']))
            except:
                pass

        def resizeEvent(self, event):   # noqa
            _window_positions[self._internal_name]['W'] = event.size().width()
            _window_positions[self._internal_name]['H'] = event.size().height()
            _window_positions[self._internal_name]['STATE'] =\
                self.windowState()
            super().resizeEvent(event)

        def moveEvent(self, event):   # noqa
            _window_positions[self._internal_name]['X'] = event.pos().x()
            _window_positions[self._internal_name]['Y'] = event.pos().y()
            super().moveEvent(event)

    _window_classes[Ret._internal_name] = Ret
    _window_positions[Ret._internal_name] = {}

    return Ret


def save_window_positions(xmlnode):
    global _window_positions, _window_classes
    import xml.etree.ElementTree as ET

    for k, v in _window_positions.items():
        nd = ET.SubElement(xmlnode, k)
        for k1, v1 in v.items():
            ET.SubElement(nd, k1).text = str(int(v1))


def set_window_positions(xmlnode):
    global _window_positions, _window_classes

    for c, p in _window_positions.items():
        nd = xmlnode.find(c)
        if nd is None:
            continue
        x, y, h, w = nd.find('X'), nd.find('Y'), nd.find('H'), nd.find('W')
        if x is not None and y is not None:
            p['X'], p['Y'] = int(x.text), int(y.text)
        if h is not None and w is not None:
            p['H'], p['W'] = int(h.text), int(w.text)
        st = nd.find('STATE')
        if st is not None:
            p['STATE'] = int(st.text)