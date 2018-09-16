import collections
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


class BAct(QtWidgets.QAction):
    def __init__(self, name, parent, actfun,
                 visfun=None, icon_code=None, hotkey=None):
        super().__init__(name, parent)
        self.triggered.connect(actfun)

        if visfun is None:
            self.visfun = lambda: True
        else:
            self.visfun = visfun

        if icon_code is not None:
            self.setIcon(QtGui.QIcon(icon_code))

        if hotkey is not None:
            self.setShortcut(hotkey)

    def define_vis(self):
        self.setEnabled(self.visfun())


class BMenu(QtWidgets.QMenu):
    def __init__(self, name, parent, menubar=None):
        super().__init__(name, parent)
        menubar.addMenu(self)
        self.aboutToShow.connect(self.define_vis)
        self.acts = collections.OrderedDict()
        self.menus = collections.OrderedDict()

    def add_action(self, name, actfun,
                   vis=None, icon_code=None, hotkey=None):
        act = BAct(name, self.parent(), actfun, vis, icon_code, hotkey)
        self.addAction(act)
        self.acts[name] = act

        return act

    def add_menu(self, menu, menufun=None):
        self.addMenu(menu)
        self.menus[menu.title()] = (menu, menufun)

    def define_vis(self):
        # actions
        for a in self.acts.values():
            a.define_vis()

        # menu
        for a in self.menus.values():
            if a[1] is not None:
                a[1](a[0])


class BLineEdit(QtWidgets.QLineEdit):
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
