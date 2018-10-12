from PyQt5 import QtWidgets, QtGui, QtCore, QtSvg


class HClusterAct(QtWidgets.QAction):
    def __init__(self, viewwin, title,
                 icon=None, hotkey=None, checkable=False):
        super().__init__(title, viewwin)

        if icon is not None:
            self.setIcon(QtGui.QIcon(icon))

        if hotkey is not None:
            self.setShortcut(hotkey)

        self.setCheckable(checkable)

        self.triggered.connect(lambda: self.do())

        self.name = title
        self.win = viewwin
        self.scene = self.win.scene

    def isactive(self):
        return True

    def ischecked(self):
        return False

    def set_checked(self):
        if self.isEnabled() and self.isCheckable():
            self.setChecked(self.ischecked())

    def do(self):
        pass


class Refresh(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, "Refresh database", icon=':/up-down')

    def isactive(self):
        return False

    def do(self):
        pass


class ClustersToDatabase(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Write clusters to database',
                         icon=':/writing')

    def do(self):
        pass


class ExportPic(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Export picture', icon=':/save')

    def do(self):
        flist = 'PNG(*.png);;SVG(*.svg)'
        ofile = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Export graph", '', flist, 'PNG(*.png)')
        if ofile[1].startswith('SVG'):
            generator = QtSvg.QSvgGenerator()
            generator.setFileName(ofile[0])
            generator.setSize(self.scene.sceneRect().size().toSize())
            generator.setViewBox(self.scene.sceneRect())
            painter = QtGui.QPainter()
            painter.begin(generator)
            self.scene.render(painter)
            painter.end()
        else:
            image = QtGui.QImage(self.scene.sceneRect().size().toSize(),
                                 QtGui.QImage.Format_ARGB32)
            image.fill(QtCore.Qt.white)
            painter = QtGui.QPainter()
            painter.begin(image)
            self.scene.render(painter)
            painter.end()
            image.save(ofile[0])


class Settings(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Settings', icon=':/settings')

    def do(self):
        pass


class FitView(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Fit view', icon=":/full-size")

    def do(self):
        self.win.view.reset_size()


class MouseMove(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Mouse move', icon=":/drag")
        if not hasattr(viewwin, 'mouse_actgroup'):
            viewwin.mouse_actgroup = QtWidgets.QActionGroup(viewwin)
        viewwin.mouse_actgroup.addAction(self)
        self.setCheckable(True)

    def do(self):
        self.win.view.set_drag_mode()


class MouseZoom(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Mouse zoom', icon=":/bw-zoom")
        if not hasattr(viewwin, 'mouse_actgroup'):
            viewwin.mouse_actgroup = QtWidgets.QActionGroup(viewwin)
        viewwin.mouse_actgroup.addAction(self)
        self.setCheckable(True)

    def do(self):
        self.win.view.set_zoom_mode()


class MouseSelect(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Mouse select', icon=":/select")
        if not hasattr(viewwin, 'mouse_actgroup'):
            viewwin.mouse_actgroup = QtWidgets.QActionGroup(viewwin)
        viewwin.mouse_actgroup.addAction(self)
        self.setCheckable(True)

    def do(self):
        self.win.view.set_select_mode()


class InspectSelection(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Inspect selection', icon=":/show-tab")

    def do(self):
        pass


class NClusterWidget(QtWidgets.QWidget):
    def __init__(self, viewwin):
        super().__init__(viewwin)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.spin = QtWidgets.QSpinBox(self)
        self.spin.setMinimum(1)
        self.spin.setMaximum(1)
        self.spin.valueChanged.connect(viewwin._act_set_igroup)
        self.layout().addWidget(QtWidgets.QLabel('N clusters'))
        self.layout().addWidget(self.spin)

    def set_value(self, val):
        self.spin.setValue(val)

    def set_maximum(self, val):
        self.spin.setMaximum(val)


class SpecSelectWidget(QtWidgets.QToolButton):
    def __init__(self, viewwin):
        super().__init__(viewwin)
        self.setText('Select')
        self.win = viewwin
        self.scene = viewwin.scene
        menu = QtWidgets.QMenu(self)
        a1 = QtWidgets.QAction('None', self)
        a2 = QtWidgets.QAction('Root', self)
        a3 = QtWidgets.QAction('All', self)
        a1.triggered.connect(self._select_none)
        a2.triggered.connect(self._select_root)
        a3.triggered.connect(self._select_all)
        menu.addActions([a1, a2, a3])
        self.setMenu(menu)
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

    def _select_none(self):
        for s in self.scene.dendrogram.steps:
            s.is_selected = False
        self.scene.dendrogram.update()

    def _select_root(self):
        for s in self.scene.dendrogram.steps:
            s.is_selected = False
        ng = self.win.spin_wdg.spin.value()
        for s in self.scene.dendrogram.get_rootsteps(ng):
            s.is_selected = True
        self.scene.dendrogram.update()

    def _select_all(self):
        for s in self.scene.dendrogram.steps:
            s.is_selected = True
        self.scene.dendrogram.update()
