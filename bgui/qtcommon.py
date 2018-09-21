import traceback
import resources   # noqa
from prog import basic
from PyQt5 import QtWidgets, QtCore, QtGui


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
        basic.log_message(traceback.format_exc(), "ERROR")
        dlg.setDetailedText(traceback.format_exc())
    dlg.setText(txt)
    dlg.setDefaultButton(dlg.button(QtWidgets.QMessageBox.Ok))
    if basic.log_message != basic._log_message:
        basic.log_message(txt)
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
    if Ret._internal_name not in _window_positions:
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

    # for c, p in _window_positions.items():
    #     nd = xmlnode.find(c)
    #     if nd is None:
    #         continue
    for nd in xmlnode:
        if nd.tag == 'MAIN':
            continue
        p = {}
        x, y, h, w = nd.find('X'), nd.find('Y'), nd.find('H'), nd.find('W')
        if x is not None and y is not None:
            p['X'], p['Y'] = int(x.text), int(y.text)
        if h is not None and w is not None:
            p['H'], p['W'] = int(h.text), int(w.text)
        st = nd.find('STATE')
        if st is not None:
            p['STATE'] = int(st.text)
        _window_positions[nd.tag] = p


class BLineEdit(QtWidgets.QLineEdit):
    """ QLineEdit with text_changed signal
        which emits on leave focus
    """
    text_changed = QtCore.pyqtSignal(str)

    def __init__(self, txt, parent):
        super().__init__(txt, parent)
        self.__curtext = txt

    def focusOutEvent(self, event):   # noqa
        if self.text() != self.__curtext:
            self.text_changed.emit(self.text())
        super().focusOutEvent(event)

    def focusInEvent(self, event):   # noqa
        self.__curtext = self.text()
        super().focusInEvent(event)


class BTextEdit(QtWidgets.QTextEdit):
    """ QTextEdit with text_changed signal
        which emits on leave focus
    """
    text_changed = QtCore.pyqtSignal(str)

    def __init__(self, txt, parent):
        super().__init__(txt, parent)
        self.__curtext = txt

    def focusOutEvent(self, event):   # noqa
        if self.toPlainText() != self.__curtext:
            self.text_changed.emit(self.toPlainText())
        super().focusOutEvent(event)

    def focusInEvent(self, event):   # noqa
        self.__curtext = self.toPlainText()
        super().focusInEvent(event)


class ELabel(QtWidgets.QLabel):
    """ QLabel with elided text
    """
    def __init__(self, parent, txt=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Widget)
        self._elide_mode = QtCore.Qt.ElideNone
        self._cached_elided_text = ''
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                           QtWidgets.QSizePolicy.Preferred)
        if txt is not None:
            self.setText(txt)

    def set_elide_mode(self, mode):
        self._elide_mode = mode
        self.updateGeometry()

    def elide_mode(self):
        return self._elide_mode

    def preferred_width(self):
        return self.fontMetrics().width(self.text()) +\
                2 * self.margin() + self.indent() + 1

    def preferred_height(self):
        return self.fontMetrics().height() + 2*self.margin()

    def setText(self, txt):   # noqa
        super().setText(txt)
        self.cache_elided_text(self.geometry().width())

    def cache_elided_text(self, w):
        w -= 2*self.margin() + self.indent()
        self._cached_elided_text = self.fontMetrics().elidedText(
                self.text(), self._elide_mode, w, QtCore.Qt.TextShowMnemonic)

    def resizeEvent(self, event):   # noqa
        super().resizeEvent(event)
        self.cache_elided_text(event.size().width())

    def paintEvent(self, event):   # noqa
        if self._elide_mode == QtCore.Qt.ElideNone:
            super().paintEvent(event)
        else:
            p = QtGui.QPainter(self)
            m = self.margin()
            if self.alignment() == QtCore.Qt.AlignCenter:
                m = 0
            else:
                m = self.margin()
            p.drawText(m + self.indent(), m,
                       self.geometry().width(),
                       self.geometry().height(),
                       self.alignment(),
                       self._cached_elided_text)
