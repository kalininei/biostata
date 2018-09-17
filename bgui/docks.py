import collections
from PyQt5 import QtWidgets, QtCore, QtGui
import resource   # noqa
from bgui import coloring
from bgui import filtdlg


class DockWidget(QtWidgets.QDockWidget):
    def __init__(self, parent, name, menu):
        super().__init__(name, parent)
        self.setObjectName(name)
        self.mainwindow = parent
        self.tmodel = None
        self.dt = None
        parent.addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        self.setVisible(False)
        # using calls through lambdas
        # because those are virtual functions.
        # Otherwise program crushes unexpectedly.
        parent.active_model_changed.connect(
                lambda: self.active_model_changed())
        parent.active_model_repr_changed.connect(
                lambda: self.repr_changed())

        menu_action = QtWidgets.QAction(name, self)
        menu_action.setCheckable(True)
        menu_action.triggered.connect(self.setVisible)
        self.visibilityChanged.connect(menu_action.setChecked)
        menu.addAction(menu_action)

    def refill(self):
        pass

    def active_model_changed(self):
        self.tmodel = self.mainwindow.active_model
        if self.tmodel is not None:
            self.dt = self.tmodel.dt
        else:
            self.dt = None

    def repr_changed(self):
        if self.isVisible():
            self.refill()


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
        buttons[1].clicked.connect(self.mainwindow._act_set_coloring)
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

    def active_model_changed(self):
        super().active_model_changed()
        if self.tmodel is not None:
            self.refill()

    def refill(self):
        self.scene = QtWidgets.QGraphicsScene()
        if self.tmodel is None:
            for b in self.btn:
                b.setEnabled(False)
        else:
            for b in self.btn:
                b.setEnabled(True)
            self.btn[0].setChecked(self.tmodel.use_coloring())
            pm = self.tmodel.coloring.draw_legend(self.frame.size())
            item = QtWidgets.QGraphicsPixmapItem(pm)
            self.scene.addItem(item)
            item.setPos(0, 0)
        self.frame.setScene(self.scene)
        self.frame.show()

    def resizeEvent(self, e):   # noqa
        self.refill()
        super().resizeEvent(e)

    def showEvent(self, e):    # noqa
        self.refill()
        super().showEvent(e)

    def _act_actbutton(self):
        if self.tmodel:
            self.tmodel.switch_coloring_mode()
            self.btn[0].setChecked(not self.btn[0].isChecked())

    def _act_change_scheme(self, step):
        if self.tmodel:
            sc = self.tmodel.get_color_scheme()
            order = sc.__class__.order
            newsc = coloring.ColorScheme.scheme_by_order(order+step)()
            newsc.copy_settings_from(sc)
            self.tmodel.set_coloring(None, newsc, None)

    def _act_revert_scheme(self, step):
        if self.tmodel:
            sc = self.tmodel.get_color_scheme()
            sc.set_reversed()
            self.tmodel.set_coloring(None, sc, None)


# ========================= Status Window
class TwoLevelTreeViewStyle(QtWidgets.QProxyStyle):
    """ Style for TwoLevelTreeView.
        Contain a special painter for drag item (a line between items)
        and ignore mouse hover algorithm.
    """
    def __init__(self, style):
        super().__init__(style)

    def drawPrimitive(self, element, option, painter, widget):  # noqa
        # disable mouse hover
        if option.state & QtWidgets.QStyle.State_MouseOver:
            option.state ^= QtWidgets.QStyle.State_MouseOver
        # draw a line under the rectangle
        if element == QtWidgets.QStyle.PE_IndicatorItemViewItemDrop:
            y = option.rect.bottomLeft().y()
            x1 = option.rect.bottomLeft().x() - widget.width()
            x2 = option.rect.bottomRight().x() + widget.width()
            pen = painter.pen()
            pen.setWidth(3)
            pen.setColor(option.palette.color(QtGui.QPalette.Highlight))
            painter.save()
            painter.setPen(pen)
            painter.drawLine(QtCore.QPoint(x1, y), QtCore.QPoint(x2, y))
            painter.restore()
        else:
            super().drawPrimitive(element, option, painter, widget)


class TwoLevelTreeView(QtWidgets.QTreeView):
    """ 2-level model view. Uses only with TwoLevelTreeModel
        Used by filter and column_info docks.
    """
    context_menu_built = QtCore.pyqtSignal(QtWidgets.QMenu)
    settings_button_clicked = QtCore.pyqtSignal(QtCore.QModelIndex)

    def __init__(self, parent):
        super().__init__(parent)
        self.__ss = []
        self.clicked.connect(self.item_clicked)
        self.setStyle(TwoLevelTreeViewStyle(self.style()))

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def _row_can_be_deleted(self, index):
        for ic in range(self.model().columnCount()):
            sib = index.sibling(index.row(), ic)
            if self.model().data(sib, TwoLevelTreeModel.RemoveButtonRole):
                return True
        return False

    def _context_menu(self, pnt):
        if self.model() is None:
            return
        menu = QtWidgets.QMenu(self)
        srows = self.selectionModel().selectedRows()
        if len(srows) > 1:
            cs = [self.model().data(i, QtCore.Qt.CheckStateRole)
                  for i in srows]
            # uncheck
            if any([x == QtCore.Qt.Unchecked for x in cs]):
                def af2():
                    for index in srows:
                        self.model().setData(index, QtCore.Qt.Checked,
                                             QtCore.Qt.CheckStateRole)

                act2 = QtWidgets.QAction("Check selected", self)
                act2.triggered.connect(af2)
                menu.addAction(act2)
            # check
            if any([x == QtCore.Qt.Checked for x in cs]):
                def af1():
                    for index in srows:
                        self.model().setData(index, QtCore.Qt.Unchecked,
                                             QtCore.Qt.CheckStateRole)

                act1 = QtWidgets.QAction("Uncheck selected", self)
                act1.triggered.connect(af1)
                menu.addAction(act1)
            # remove
            can_be_deleted = list(filter(
                    lambda x: self._row_can_be_deleted(x), srows))
            if len(can_be_deleted) > 0:
                def af3():
                    for index in sorted(can_be_deleted,
                                        key=lambda x: x.row(),
                                        reverse=True):
                        self.model().remove_row(index)

                act3 = QtWidgets.QAction("Remove selected", self)
                act3.triggered.connect(af3)
                menu.addAction(act3)

        self.context_menu_built.emit(menu)
        menu.popup(self.viewport().mapToGlobal(pnt))

    def setModel(self, model):   # noqa
        super().setModel(model)
        self.expandAll()

    def event(self, e):
        # it seems this is the only event which is called
        # strictly after dragdrop and strictly once.
        # so we place handler here
        if e.type() == QtCore.QEvent.ChildRemoved:
            if self.__ss:
                self.select_by_colnames(self.__ss)
                self.model().set_drag_group(-1)
                self.__ss = []
        return super().event(e)

    def startDrag(self, action):   # noqa
        ind = self.selectionModel().currentIndex()
        if ind.parent():
            # forbid drag if selection contain different groups
            gr = set()
            for ind in self.selectionModel().selectedRows():
                if ind.parent():
                    gr.add(ind.parent().row())
            if len(gr) != 1:
                return
            # allow moves only within current group
            self.model().set_drag_group(ind.parent().row())
            # save selection in order to restore it
            self.__ss = []
            for ind in self.selectionModel().selectedRows():
                self.__ss.append(ind.data(TwoLevelTreeModel.SubDataRole))
            super().startDrag(action)

    def item_clicked(self, index):
        # remove button click
        if self.model().data(index, TwoLevelTreeModel.RemoveButtonRole):
            self.model().remove_row(index)
        # settings button click
        if self.model().data(index, TwoLevelTreeModel.SettingsButtonRole):
            self.settings_button_clicked.emit(index)

    def dragMoveEvent(self, e):   # noqa
        self.setDropIndicatorShown(True)
        super().dragMoveEvent(e)

    def select_by_colnames(self, cnames):
        new_selection = QtCore.QItemSelection()
        flags = (QtCore.QItemSelectionModel.Select |
                 QtCore.QItemSelectionModel.Rows)
        for c in cnames:
            index = self.model().match(self.model().index(0, 0),
                                       TwoLevelTreeModel.SubDataRole,
                                       c, 1, QtCore.Qt.MatchRecursive)
            for ind in index:
                new_selection.select(ind, ind)

        self.selectionModel().clearSelection()
        self.selectionModel().select(new_selection, flags)


class TwoLevelTreeModel(QtGui.QStandardItemModel):
    """ 2-level tree with coordinated checkboxes model:
        top level is fixed.
        Used for filter and column_info treeviews
    """
    # Roles
    SubDataRole = QtCore.Qt.UserRole + 1
    RemoveButtonRole = QtCore.Qt.UserRole + 2
    SettingsButtonRole = QtCore.Qt.UserRole + 3
    # signals
    changed_by_user = QtCore.pyqtSignal()

    def __init__(self, top_level_items):
        super().__init__()
        self.__drag_group = -1
        self.tli = []
        for n in top_level_items:
            self.tli.append(QtGui.QStandardItem())
            self.tli[-1].setText(n)
            self.appendRow(self.tli[-1])
        self.itemChanged.connect(self.item_changed)
        self.this_from_external()

    def set_drag_group(self, igr):
        # only childs of igr-th row will be availible for a drag
        self.__drag_group = igr

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        ret = QtCore.Qt.ItemIsEnabled
        if index.column() == 0:
            ret = ret | QtCore.Qt.ItemIsUserCheckable
        if index.parent().isValid():
            ret = ret | QtCore.Qt.ItemIsSelectable
            ret = ret | QtCore.Qt.ItemIsDragEnabled
        elif index.column() == 0 and index.row() == self.__drag_group:
            ret = ret | QtCore.Qt.ItemIsDropEnabled
        return ret

    def set_checked(self, vislist):
        for it in self.tli:
            for ich in range(it.rowCount()):
                ch = it.child(ich)
                cond = ch.data(QtCore.Qt.DisplayRole) in vislist
                nv = QtCore.Qt.Checked if cond else QtCore.Qt.Unchecked
                ch.setData(nv, QtCore.Qt.CheckStateRole)

    def remove_row(self, index):
        self.removeRow(index.row(), index.parent())
        self._set_tli_checks()
        self.changed_by_user.emit()

    def add_row(self, parent_row, items):
        self.tli[parent_row].appendRow(items)
        self._set_tli_checks()
        self.changed_by_user.emit()

    def item_changed(self, item):
        if item.column() == 0:
            if item.parent():
                self._set_tli_checks()
            else:
                self.itemChanged.disconnect(self.item_changed)
                for i in range(item.rowCount()):
                    item.child(i).setCheckState(item.checkState())
                self.itemChanged.connect(self.item_changed)
            self.changed_by_user.emit()

    def _set_tli_checks(self):
        self.itemChanged.disconnect(self.item_changed)
        for itm in self.tli:
            usd = []
            for i in range(itm.rowCount()):
                if itm.child(i):
                    usd.append(itm.child(i).checkState())
            if len(usd) == 0:
                itm.setCheckState(QtCore.Qt.Unchecked)
            elif len(set(usd)) == 1:
                itm.setCheckState(usd[0])
            else:
                itm.setCheckState(QtCore.Qt.PartiallyChecked)
        self.itemChanged.connect(self.item_changed)

    def dropMimeData(self, data, action, row, column, parent):   # noqa
        # if we drop on parent -> forces drop on the first child
        row = max(0, row)
        # if we drop on another column -> prevents data shift
        column = 0
        return super().dropMimeData(data, action, row, column, parent)

    def this_from_external(self):
        for itm in self.tli:
            itm.removeRows(0, itm.rowCount())
        self._imp_this_from_external()
        self._set_tli_checks()

    def external_from_this(self):
        self._imp_external_from_this()

    def _imp_this_from_external(self):
        pass

    def _imp_external_from_this(self):
        pass


class TwoLevelTreeDockWidget(DockWidget):
    """ base class for filter and column info docks
    """
    def __init__(self, parent, name, menu):
        super().__init__(parent, name, menu)
        # main frame = TreeWidget + buttonbox
        frame = QtWidgets.QFrame(self)
        self.setWidget(frame)
        frame.setLayout(QtWidgets.QVBoxLayout())
        frame.layout().setContentsMargins(0, 0, 0, 0)
        frame.layout().setSpacing(0)
        self.tab = TwoLevelTreeView(self)
        self.tab.setHeaderHidden(True)
        self.tab.setFrameShape(QtWidgets.QFrame.NoFrame)
        frame.layout().addWidget(self.tab)

        # buttons
        self.buttonbox = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Apply |
                QtWidgets.QDialogButtonBox.Cancel)
        self.buttonbox.setEnabled(False)
        self.buttonbox.setVisible(False)
        self.buttonbox.clicked.connect(self.apply_cancel_clicked)
        frame.layout().addWidget(self.buttonbox)

    def internal_change(self):
        self._wait_for_apply(True)

    def showEvent(self, e):   # noqa
        self.refill()
        super().showEvent(e)

    def apply_cancel_clicked(self, button):
        br = self.buttonbox.buttonRole(button)
        if br == QtWidgets.QDialogButtonBox.ApplyRole:
            # make changes
            self.tab.model().external_from_this()
            self.mainwindow.active_model.update()
        else:
            # return to original state
            self.refill()

    def _wait_for_apply(self, status):
        self.buttonbox.setVisible(status)
        self.buttonbox.setEnabled(status)

        p = self.tab.palette()
        if status:
            brush = QtGui.QBrush(QtGui.QColor(255, 235, 235, 255))
        else:
            brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 255))
        p.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        self.tab.setPalette(p)

    def refill(self):
        if self.tmodel:
            # refill model
            self.tab.model().this_from_external()
            # disable apply button
            self._wait_for_apply(False)


# ============================= ColumnInfoDock
class ColumnInfoModel(TwoLevelTreeModel):
    def __init__(self, dt=None):
        self.dt = dt
        self.newcolumns = collections.OrderedDict()
        super().__init__(["Categorical", "Real"])
        self.setColumnCount(3)

    def _imp_this_from_external(self):
        for c in self.dt.all_columns[1:]:
            itm = []
            itm.append(QtGui.QStandardItem())
            itm[0].setData(c.name, TwoLevelTreeModel.SubDataRole)
            itm[0].setText(c.name)
            cs = QtCore.Qt.Checked if c in self.dt.visible_columns else\
                QtCore.Qt.Unchecked
            itm[0].setCheckState(cs)
            itm.append(QtGui.QStandardItem())
            itm[1].setText(c.col_type())
            if not c.is_original():
                itm.append(QtGui.QStandardItem())
                itm[2].setIcon(QtGui.QIcon(':/remove'))
                itm[2].setData(True, TwoLevelTreeModel.RemoveButtonRole)
            if c.dt_type != "REAL":
                self.tli[0].appendRow(itm)
            else:
                self.tli[1].appendRow(itm)

    def _imp_external_from_this(self):
        cols, cnames, vis = [], [], []
        for itm in self.tli:
            for i in range(itm.rowCount()):
                item = itm.child(i)
                cnames.append(item.data(TwoLevelTreeModel.SubDataRole))
                vis.append(item.checkState() == QtCore.Qt.Checked)
        for c in cnames:
            try:
                cols.append(self.dt.columns[c])
            except:
                cols.append(self.newcolumns[c])
        # remove columns
        for c in self.dt.all_columns[1:]:
            if c not in cols:
                self.dt.remove_column(c)
        # add columns
        for i, (k, v) in enumerate(zip(cols, vis)):
            self.dt.add_column(k, i+1, v)


class ColumnInfoDockWidget(TwoLevelTreeDockWidget):
    def __init__(self, parent, menu):
        super().__init__(parent, "Columns visibility", menu)
        # selection behaiviour: allow selection for child lines only
        self.tab.setSelectionMode(
                QtWidgets.QAbstractItemView.ExtendedSelection)
        # drag drop
        self.tab.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

    def active_model_changed(self):
        super().active_model_changed()
        if self.dt is not None:
            model = ColumnInfoModel(self.dt)
            model.changed_by_user.connect(self.internal_change)
            self.tab.setModel(model)
            self.tab.header().setStretchLastSection(False)
            self.tab.header().setSectionResizeMode(
                     1, QtWidgets.QHeaderView.Stretch)
            self.tab.resizeColumnToContents(0)
            self.tab.resizeColumnToContents(1)
            self.tab.setColumnWidth(2, 20)
        else:
            self.tab.setModel(None)

    def refill(self):
        super().refill()
        self.tab.resizeColumnToContents(0)
        self.tab.resizeColumnToContents(1)


# ============================= Filters Dock
class FiltersInfoModel(TwoLevelTreeModel):
    def __init__(self, dt=None):
        self.dt = dt
        super().__init__(["Named", "Anonymous"])
        self.setColumnCount(3)

    def _imp_this_from_external(self):
        for f in self.dt.proj.named_filters:
            if f.is_applicable(self.dt):
                cs = QtCore.Qt.Checked if f in self.dt.used_filters else\
                    QtCore.Qt.Unchecked
                self._add_new_filter(f, cs)
        for f in self.dt.all_anon_filters:
            cs = QtCore.Qt.Checked if f in self.dt.used_filters else\
                QtCore.Qt.Unchecked
            self._add_new_filter(f, cs)

    def _imp_external_from_this(self):
        anon_filters, vis_filters = [], []
        for i in range(self.tli[1].rowCount()):
            itm = self.tli[1].child(i)
            f = itm.data(TwoLevelTreeModel.SubDataRole)
            anon_filters.append(f)
            if itm.checkState() == QtCore.Qt.Checked:
                vis_filters.append(anon_filters[-1])
        named_filters = [x for x in self.dt.proj.named_filters
                         if not x.is_applicable(self.dt)]
        for i in range(self.tli[0].rowCount()):
            itm = self.tli[0].child(i)
            f = itm.data(TwoLevelTreeModel.SubDataRole)
            named_filters.append(f)
            if itm.checkState() == QtCore.Qt.Checked:
                vis_filters.append(named_filters[-1])
        self.dt.set_named_filters(named_filters)
        self.dt.set_anon_filters(anon_filters)
        self.dt.set_active_filters(vis_filters)

    def _add_new_filter(self, f, useit=True):
        itm = [QtGui.QStandardItem() for _ in range(3)]
        itm[0].setData(f, TwoLevelTreeModel.SubDataRole)
        itm[0].setToolTip(f.to_multiline())
        itm[0].setCheckState(QtCore.Qt.Checked if useit
                             else QtCore.Qt.Unchecked)
        itm[1].setIcon(QtGui.QIcon(':/settings'))
        itm[1].setData(True, TwoLevelTreeModel.SettingsButtonRole)
        itm[2].setIcon(QtGui.QIcon(':/remove'))
        itm[2].setData(True, TwoLevelTreeModel.RemoveButtonRole)
        if f.name:
            itm[0].setText(f.name)
            self.add_row(0, itm)
        else:
            itm[0].setText(f.to_singleline())
            self.add_row(1, itm)


class FiltersDockWidget(TwoLevelTreeDockWidget):
    def __init__(self, parent, menu):
        super().__init__(parent, "Filters", menu)
        # tab
        self.tab.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tab.context_menu_built.connect(self._filters_context_menu)
        self.tab.settings_button_clicked.connect(self._filter_settings)

    def active_model_changed(self):
        super().active_model_changed()
        if self.dt is not None:
            model = FiltersInfoModel(self.dt)
            self.tab.setModel(model)
            model.changed_by_user.connect(self.internal_change)
            self.tab.header().setStretchLastSection(False)
            self.tab.header().setSectionResizeMode(
                    0, QtWidgets.QHeaderView.Stretch)
            self.tab.setColumnWidth(1, 20)
            self.tab.setColumnWidth(2, 20)
        else:
            self.tab.setModel(None)

    def _used_named_filters(self):
        model = self.tab.model()
        used_names = set([x.name for x in model.dt.proj.named_filters
                          if x.is_applicable(model.dt)])
        for i in range(model.tli[0].rowCount()):
            ch = model.tli[0].child(i)
            used_names.add(ch.data(TwoLevelTreeModel.SubDataRole).name)
        return used_names

    def _filters_context_menu(self, menu):
        model = self.tab.model()
        menu.addSeparator()
        act = [QtWidgets.QAction("Deactivate all", self),
               QtWidgets.QAction("Remove all named", self),
               QtWidgets.QAction("Remove all anonymous", self),
               QtWidgets.QAction("New filter...", self)]

        def a1():
            model.tli[0].setCheckState(QtCore.Qt.Unchecked)
            model.tli[1].setCheckState(QtCore.Qt.Unchecked)

        def a2():
            for i in reversed(range(model.tli[0].rowCount())):
                ch = model.tli[0].child(i)
                model.remove_row(ch.index())

        def a3():
            for i in reversed(range(model.tli[1].rowCount())):
                ch = model.tli[1].child(i)
                model.remove_row(ch.index())

        def a4():
            used_names = self._used_named_filters()
            dialog = filtdlg.EditFilterDialog(
                    None, model.dt, used_names, self)
            if dialog.exec_():
                model._add_new_filter(dialog.ret_value(), True)

        for a, fun in zip(act, [a1, a2, a3, a4]):
            a.triggered.connect(fun)
            menu.addAction(a)

    def _filter_settings(self, ind):
        index = ind.sibling(ind.row(), 0)
        used_names = self._used_named_filters()
        f = self.tab.model().data(index, TwoLevelTreeModel.SubDataRole)
        dialog = filtdlg.EditFilterDialog(
                f, self.tab.model().dt, used_names, self)
        if dialog.exec_():
            ret = dialog.ret_value()
            if ret.name == f.name:
                # if filter naming is not changed -> copy properties
                f.copy_from(ret)
                tp = ret.to_multiline()
                nm = ret.to_singleline() if ret.name is None else ret.name
                self.tab.model().setData(index, tp, QtCore.Qt.ToolTipRole)
                self.tab.model().setData(index, nm, QtCore.Qt.DisplayRole)
            else:
                # if filter naming is changed -> remove old, add new
                used = (index.data(QtCore.Qt.CheckStateRole) ==
                        QtCore.Qt.Checked)
                self.tab.model().remove_row(index)
                self.tab.model()._add_new_filter(ret, used)
