from PyQt5 import QtWidgets, QtCore, QtGui
import resource   # noqa
from bgui import coloring


class DockWidget(QtWidgets.QDockWidget):
    def __init__(self, parent, name, menu):
        super().__init__(name, parent)
        parent.addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        self.setVisible(False)

        menu_action = QtWidgets.QAction(name, self)
        menu_action.setCheckable(True)
        menu_action.triggered.connect(self.setVisible)
        self.visibilityChanged.connect(menu_action.setChecked)
        menu.addAction(menu_action)

    def active_model_changed(self):
        pass


# ======================= Color legend
class ColorDockWidget(DockWidget):
    def __init__(self, parent, menu):
        super().__init__(parent, "Color legend", menu)
        # mainframe
        mainframe = QtWidgets.QFrame(self)
        mainframe.setLayout(QtWidgets.QHBoxLayout())
        mainframe.layout().setSpacing(0)
        mainframe.layout().setStretch(0, 1)
        mainframe.layout().setStretch(1, 0)
        mainframe.setFrameShape(QtWidgets.QFrame.NoFrame)
        mainframe.layout().setContentsMargins(0, 0, 0, 0)
        self.setWidget(mainframe)

        # picture frame
        self.frame = QtWidgets.QGraphicsView(mainframe)
        self.frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        mainframe.layout().addWidget(self.frame)

        # button frame
        buttframe = QtWidgets.QFrame(mainframe)
        buttframe.setLayout(QtWidgets.QVBoxLayout())
        buttframe.layout().setSpacing(0)
        buttframe.setFrameShape(QtWidgets.QFrame.NoFrame)
        buttframe.layout().setContentsMargins(0, 0, 0, 0)
        mainframe.layout().addWidget(buttframe)

        # buttons
        buttons = []
        self.btn = buttons
        for i in range(5):
            buttons.append(QtWidgets.QPushButton(buttframe))
            buttons[-1].setFixedSize(25, 25)
            buttframe.layout().addWidget(buttons[-1])
            buttons[-1].setFocusPolicy(QtCore.Qt.NoFocus)
            buttons[-1].setIconSize(QtCore.QSize(16, 16))
        buttframe.layout().addStretch(1)
        # activation button
        ico0 = QtGui.QIcon()
        ico0.addFile(':/activate-on', state=QtGui.QIcon.On)
        ico0.addFile(':/activate-off', state=QtGui.QIcon.Off)
        buttons[0].setCheckable(True)
        buttons[0].setIcon(ico0)
        buttons[0].setToolTip("Toggle coloring activation")
        buttons[0].pressed.connect(self._act_actbutton)
        # settings button
        buttons[1].setIcon(QtGui.QIcon(':/settings'))
        buttons[1].setToolTip("Coloring settings")
        buttons[1].clicked.connect(self.parent()._act_set_coloring)
        # next color scheme
        buttons[2].setIcon(QtGui.QIcon(':/next-item'))
        buttons[2].setToolTip("Next color scheme")
        buttons[2].clicked.connect(lambda: self._act_change_scheme(1))
        # previous color scheme
        buttons[3].setIcon(QtGui.QIcon(':/prev-item'))
        buttons[3].setToolTip("Previous color scheme")
        buttons[3].clicked.connect(lambda: self._act_change_scheme(-1))
        # revert
        buttons[4].setIcon(QtGui.QIcon(':/up-down'))
        buttons[4].setToolTip("Revert color scheme")
        buttons[4].clicked.connect(self._act_revert_scheme)

    def refill(self):
        if self.parent().active_model is None:
            for b in self.btn:
                b.setEnabled(False)
        for b in self.btn:
            b.setEnabled(True)
        self.btn[0].setChecked(self.parent().active_model.use_coloring())
        pm = self.parent().active_model.coloring.draw_legend(
                    self.frame.size())
        self.scene = QtWidgets.QGraphicsScene()
        self.frame.setScene(self.scene)
        item = QtWidgets.QGraphicsPixmapItem(pm)
        self.scene.addItem(item)
        item.setPos(0, 0)
        self.frame.show()

    def resizeEvent(self, e):   # noqa
        self.refill()
        super().resizeEvent(e)

    def showEvent(self, e):    # noqa
        self.refill()
        super().showEvent(e)

    def _act_actbutton(self):
        if self.parent().active_model:
            self.parent().active_model.switch_coloring_mode()
            self.btn[0].setChecked(not self.btn[0].isChecked())

    def _act_change_scheme(self, step):
        sc = self.parent().active_model.get_color_scheme()
        order = sc.__class__.order
        newsc = coloring.ColorScheme.scheme_by_order(order+step)()
        newsc.copy_settings_from(sc)
        self.parent().active_model.set_coloring(None, newsc, None)

    def _act_revert_scheme(self, step):
        sc = self.parent().active_model.get_color_scheme()
        sc.set_reversed()
        self.parent().active_model.set_coloring(None, sc, None)


class StatusDockWidget(DockWidget):
    def __init__(self, parent, menu):
        super().__init__(parent, "Status window", menu)


class FiltersDockWidget(DockWidget):
    def __init__(self, parent, menu):
        super().__init__(parent, "Filters", menu)
