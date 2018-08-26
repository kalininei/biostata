import collections
from PyQt5 import QtWidgets, QtCore, QtGui
import resource   # noqa
from bgui import coloring
from bgui import filtdlg


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


# ======================= Filter Dock
class FiltersDockWidget(DockWidget):
    def __init__(self, parent, menu):
        super().__init__(parent, "Filters", menu)
        # internal filter structure: filter->[can_be_used, is_used, item]
        self.anon_filters = collections.OrderedDict()
        self.named_filters = collections.OrderedDict()

        # main frame = TreeWidget + buttonbox
        frame = QtWidgets.QFrame(self)
        self.setWidget(frame)
        frame.setLayout(QtWidgets.QVBoxLayout())
        frame.layout().setContentsMargins(0, 0, 0, 0)
        frame.layout().setSpacing(0)

        # tab
        self.tab = QtWidgets.QTreeWidget(self)
        self.itm_named = QtWidgets.QTreeWidgetItem(self.tab)
        self.itm_anon = QtWidgets.QTreeWidgetItem(self.tab)
        self.itm_named.setExpanded(True)
        self.itm_anon.setExpanded(True)
        self.itm_named.setText(0, "Named")
        self.itm_anon.setText(0, "Anonymous")
        self.tab.setColumnCount(3)
        self.tab.setHeaderHidden(True)
        self.tab.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.tab.setHeaderHidden(True)
        self.tab.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tab.header().setStretchLastSection(False)
        self.tab.header().setSectionResizeMode(
                0, QtWidgets.QHeaderView.Stretch)
        self.tab.setColumnWidth(1, 20)
        self.tab.setColumnWidth(2, 20)
        self.tab.itemChanged.connect(self.item_changed)
        self.tab.itemClicked.connect(self.item_clicked)
        frame.layout().addWidget(self.tab)

        # context menu
        self.tab.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tab.customContextMenuRequested.connect(self._context_menu)

        # buttons
        self.buttonbox = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Apply |
                QtWidgets.QDialogButtonBox.Cancel)
        self.buttonbox.setEnabled(False)
        self.buttonbox.clicked.connect(self.apply_cancel_clicked)
        frame.layout().addWidget(self.buttonbox)

    def showEvent(self, e):   # noqa
        self.refill()
        super().showEvent(e)

    def _context_menu(self, pnt):
        menu = QtWidgets.QMenu(self)
        act1 = QtWidgets.QAction("Deactivate all", self)
        act2 = QtWidgets.QAction("Remove all named", self)
        act3 = QtWidgets.QAction("Remove all anonymous", self)
        act4 = QtWidgets.QAction("New filter...", self)

        def a1():
            self.itm_anon.setCheckState(0, QtCore.Qt.Unchecked)
            self.itm_named.setCheckState(0, QtCore.Qt.Unchecked)

        def a2():
            self.named_filters.clear()
            self._fill_from_internal_structure()
            self._wait_for_apply(True)

        def a3():
            self.anon_filters.clear()
            self._fill_from_internal_structure()
            self._wait_for_apply(True)

        def a4():
            used_names = [x.name for x in self.named_filters]
            dialog = filtdlg.EditFilterDialog(
                    None, self.parent().active_model.dt, used_names, self)
            if dialog.exec_():
                self._new_filter_to_internal_structure(
                    dialog.ret_value(), True)
                self._wait_for_apply(True)

        act1.triggered.connect(a1)
        act2.triggered.connect(a2)
        act3.triggered.connect(a3)
        act4.triggered.connect(a4)
        menu.addAction(act1)
        menu.addAction(act2)
        menu.addAction(act3)
        menu.addAction(act4)

        menu.popup(self.tab.viewport().mapToGlobal(pnt))

    def apply_cancel_clicked(self, button):
        br = self.buttonbox.buttonRole(button)
        if br == QtWidgets.QDialogButtonBox.ApplyRole:
            # make changes
            self._write_from_internal_structure(self.parent().active_model.dt)
            self.parent().active_model.update()
        else:
            # return to original state
            self.refill()

    def _filter_by_witem(self, item):
        if item.parent() == self.itm_anon:
            return next((k for k, v in self.anon_filters.items()
                        if v[2] == item), None)
        elif item.parent() == self.itm_named:
            return next((k for k, v in self.named_filters.items()
                        if v[2] == item), None)
        return None

    def item_clicked(self, item, column):
        # ignore parent items
        fnd = self._filter_by_witem(item)
        if not fnd:
            return
        if column == 1:
            # settings
            used_names = [x.name for x in self.named_filters]
            dialog = filtdlg.EditFilterDialog(
                    fnd, self.parent().active_model.dt, used_names, self)
            if dialog.exec_():
                ret = dialog.ret_value()
                if ret.name == fnd.name:
                    # if filter naming is not changed -> copy properties
                    fnd.copy_from(dialog.ret_value())
                    item.setToolTip(0, ret.to_multiline())
                    if ret.name is None:
                        item.setText(0, ret.to_singleline())
                else:
                    # if filter naming is changed -> remove old, add new
                    self.item_clicked(item, 2)
                    used = (item.checkState(0) == QtCore.Qt.Checked)
                    self._new_filter_to_internal_structure(ret, used)
                self._wait_for_apply(True)
        elif column == 2:
            # remove item
            if item.parent() == self.itm_anon:
                self.anon_filters.pop(fnd)
                self.itm_anon.removeChild(item)
            elif item.parent() == self.itm_named:
                self.named_filters.pop(fnd)
                self.itm_named.removeChild(item)
            self._wait_for_apply(True)

    def item_changed(self, item, column):
        self.tab.itemChanged.disconnect(self.item_changed)
        if column == 0:
            # check state changed
            if item == self.itm_named:
                for i in range(self.itm_named.childCount()):
                    self.itm_named.child(i).setCheckState(
                            0, self.itm_named.checkState(0))
            elif item == self.itm_anon:
                for i in range(self.itm_anon.childCount()):
                    self.itm_anon.child(i).setCheckState(
                            0, self.itm_anon.checkState(0))
            else:
                self._set_parent_checks()
            self._update_internal_structure()
            self._wait_for_apply(True)
        self.tab.itemChanged.connect(self.item_changed)

    def _wait_for_apply(self, status):
        self.buttonbox.setEnabled(status)

        p = self.tab.palette()
        if status:
            brush = QtGui.QBrush(QtGui.QColor(255, 235, 235, 255))
        else:
            brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 255))
        p.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        self.tab.setPalette(p)

    def refill(self):
        # read from data
        self._read_to_internal_structure(self.parent().active_model.dt)
        # draw tree
        self._fill_from_internal_structure()
        # disable apply button
        self._wait_for_apply(False)

    def _new_filter_to_internal_structure(self, f, useit=True):
        if f.name:
            self.named_filters[f] = [True, useit, None]
        else:
            self.anon_filters[f] = [True, useit, None]
        self._fill_from_internal_structure()

    def _read_to_internal_structure(self, mod):
        """ data table -> internal structure """
        # filter: can_be_used, is_used
        self.anon_filters.clear()
        self.named_filters.clear()
        # named
        for f in mod.proj.named_filters:
            self.named_filters[f] = [f.is_applicable(mod),
                                     f in mod.used_filters,
                                     None]
        # anon
        for f in mod.all_anon_filters:
            self.anon_filters[f] = [True, f in mod.used_filters, None]

    def _write_from_internal_structure(self, mod):
        """ internal structure -> data table """
        mod.set_named_filters(self.named_filters.keys())
        mod.set_anon_filters(self.anon_filters.keys())
        actfilt = [k for k, v in self.named_filters.items() if v[1]] +\
                  [k for k, v in self.anon_filters.items() if v[1]]
        mod.set_active_filters(actfilt)

    def _fill_from_internal_structure(self):
        """ internal structure -> widget """
        self.tab.itemChanged.disconnect(self.item_changed)
        # clear all
        for i in reversed(range(self.itm_named.childCount())):
            ch = self.itm_named.child(i)
            self.itm_named.removeChild(ch)
        for i in reversed(range(self.itm_anon.childCount())):
            ch = self.itm_anon.child(i)
            self.itm_anon.removeChild(ch)
        # fill
        for k, v in self.anon_filters.items():
            if v[0]:
                self.add_anon_filter(k, v)
        for k, v in self.named_filters.items():
            if v[0]:
                self.add_named_filter(k, v)
        self._set_parent_checks()
        self.tab.itemChanged.connect(self.item_changed)

    def _update_internal_structure(self):
        """ widget -> internal structure """
        i = 0
        for k, v in self.anon_filters.items():
            if v[0]:
                cs = self.itm_anon.child(i).checkState(0)
                v[1] = (cs == QtCore.Qt.Checked)
                i += 1
        i = 0
        for k, v in self.named_filters.items():
            if v[0]:
                cs = self.itm_named.child(i).checkState(0)
                v[1] = (cs == QtCore.Qt.Checked)
                i += 1

    def _set_parent_checks(self):
        def ap(par):
            usd = []
            for i in range(par.childCount()):
                usd.append(par.child(i).checkState(0))
            if len(usd) == 0:
                par.setCheckState(0, QtCore.Qt.Unchecked)
            elif len(set(usd)) == 1:
                par.setCheckState(0, usd[0])
            else:
                par.setCheckState(0, QtCore.Qt.PartiallyChecked)

        ap(self.itm_named)
        ap(self.itm_anon)

    def _set_item(self, itm, f, opts):
        cs = QtCore.Qt.Checked if opts[1] else QtCore.Qt.Unchecked
        opts[2] = itm
        itm.setToolTip(0, f.to_multiline())
        itm.setCheckState(0, cs)
        itm.setText(0, f.name)
        itm.setIcon(1, QtGui.QIcon(":/settings"))
        itm.setIcon(2, QtGui.QIcon(":/remove"))

    def add_anon_filter(self, f, opts):
        itm = QtWidgets.QTreeWidgetItem(self.itm_anon)
        self._set_item(itm, f, opts)
        itm.setText(0, f.to_singleline())

    def add_named_filter(self, f, opts):
        itm = QtWidgets.QTreeWidgetItem(self.itm_named)
        self._set_item(itm, f, opts)


# ========================= Status Window
class StatusDockWidget(DockWidget):
    def __init__(self, parent, menu):
        super().__init__(parent, "Status window", menu)
