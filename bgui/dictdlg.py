import functools
import collections
import copy
from PyQt5 import QtWidgets, QtCore
from bgui import dlgs
from bgui import qtcommon


class EditDictModel(QtCore.QAbstractTableModel):
    def __init__(self, uvals=None, editdict=None):
        super().__init__()
        self.mode = "ENUM"
        self.editable = True
        self.keys = [None] * 2
        self.values = [''] * 2
        self.comments = [''] * 2
        if uvals is not None:
            self.values = uvals[:]
            self.keys = list(range(len(uvals)))
            self.comments = [''] * len(uvals)
        elif editdict is not None:
            self.reset_dict(editdict)

    def columnCount(self, index=None):   # noqa
        return 3

    def rowCount(self, index=None):   # noqa
        if self.mode == "ENUM":
            return len(self.keys)
        else:
            return 2

    def data(self, index, role):
        if not index.isValid():
            return None

        if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
            if index.column() == 0:
                if self.mode == "BOOL":
                    return index.row()
                else:
                    return self.keys[index.row()]
            elif index.column() == 1:
                return self.values[index.row()]
            elif index.column() == 2:
                return self.comments[index.row()]

    def flags(self, index):
        ret = QtCore.Qt.ItemIsEnabled
        if self.editable and not (self.mode == "BOOL" and index.column() == 0):
            ret = ret | QtCore.Qt.ItemIsEditable
        return ret

    def setData(self, index, value, role):   # noqa
        if not index.isValid():
            return None
        if role == QtCore.Qt.EditRole:
            if index.column() == 0:
                try:
                    self.keys[index.row()] = int(value)
                except:
                    return False
            elif index.column() == 1:
                self.values[index.row()] = value.strip()
            elif index.column() == 2:
                self.comments[index.row()] = value.strip()
            return True

    def headerData(self, index, orient, role):   # noqa
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Horizontal:
            return ["key (int)", "value (str)", "comments"][index]

    def set_mode(self, mode):
        self.beginResetModel()
        self.mode = mode
        self.endResetModel()

    def set_length(self, n):
        self.beginResetModel()
        self.keys = (self.keys + [None] * n)[:n]
        self.values = (self.values + [''] * n)[:n]
        self.comments = (self.comments + [''] * n)[:n]
        self.endResetModel()

    def autokeys(self):
        self.beginResetModel()
        self.keys = list(range(len(self.keys)))
        self.endResetModel()

    def reset_dict(self, editdict):
        self.keys = editdict.keys()
        self.values = editdict.values()
        self.comments = editdict.comments()
        self.set_mode(editdict.dt_type)

    def get_keys(self):
        if self.mode == "BOOL":
            return [0, 1]
        else:
            return list(map(int, self.keys))

    def get_values(self):
        return list(map(lambda x: x.strip() if x else '', self.values))

    def get_comms(self):
        return list(map(lambda x: x.strip() if x else '', self.comments))


class EditDictView(QtWidgets.QTableView):
    def __init__(self, parent, uvals=None, editdict=None):
        super().__init__(parent)
        self.setModel(EditDictModel(uvals, editdict))
        self.verticalHeader().setVisible(False)


@qtcommon.hold_position
class CreateNewDictionary(dlgs.OkCancelDialog):
    def __init__(self, projdict, parent, tp=None,
                 uvals=None, can_change_type=True):
        super().__init__("Create/Edit dictionary", parent, "grid")
        self.resize(400, 300)
        self._ret_value = None
        self._ignore_name = ''
        self.projdict = projdict
        if uvals is not None:
            if len(uvals) == 0:
                uvals = [None, None]
            elif len(uvals) == 1:
                uvals = [uvals[0], None]

        self.mainframe.layout().addWidget(
                QtWidgets.QLabel("Dictionary name"), 0, 0)
        self.e_name = QtWidgets.QLineEdit(self.get_autoname(), self)
        self.mainframe.layout().addWidget(self.e_name, 0, 1)

        self.mainframe.layout().addWidget(
                QtWidgets.QLabel("Dictionary type"), 1, 0)
        self.e_type = QtWidgets.QComboBox(self)
        self.e_type.addItems(["ENUM", "BOOL"])
        if tp is not None:
            self.e_type.setCurrentText(tp)
        else:
            self.e_type.setCurrentIndex(0)
        self.mainframe.layout().addWidget(self.e_type, 1, 1)

        self.e_spin = QtWidgets.QSpinBox(self)
        self.e_spin.setMinimum(2)
        if uvals is not None:
            self.e_spin.setValue(len(uvals))
        else:
            self.e_spin.setValue(2)
        if tp and tp == "BOOL":
            self.e_spin.setEnabled(False)
        self.e_type.currentTextChanged.connect(
            lambda txt: self.e_spin.setEnabled(txt == "ENUM"))

        self.mainframe.layout().addWidget(
                QtWidgets.QLabel("Keys count"), 2, 0)
        self.mainframe.layout().addWidget(self.e_spin, 2, 1)

        self.autofill = QtWidgets.QPushButton("Auto keys")
        self.mainframe.layout().addWidget(self.autofill, 3, 1)
        p = QtWidgets.QSizePolicy()
        p.setHorizontalPolicy(QtWidgets.QSizePolicy.Fixed)
        self.autofill.setSizePolicy(p)

        self.e_table = EditDictView(self, uvals)
        if tp is not None:
            self.e_table.model().set_mode(tp)
        self.e_type.currentTextChanged.connect(self.e_table.model().set_mode)
        self.e_spin.valueChanged.connect(self.e_table.model().set_length)
        self.autofill.clicked.connect(self.e_table.model().autokeys)
        self.mainframe.layout().addWidget(self.e_table, 4, 0, 1, 2)

        if tp is not None and not can_change_type:
            self.e_type.setEnabled(False)

    def set_values_from(self, editdict):
        self._ignore_name = editdict.name
        self.e_name.setText(editdict.name)
        self.e_spin.setValue(editdict.count())
        self.e_table.model().reset_dict(editdict)
        self.e_type.setCurrentText(editdict.dt_type)

    def get_autoname(self):
        i = 1
        while True:
            nm = "dictionary {}".format(i)
            if nm in self.projdict:
                i += 1
            else:
                break
        return nm

    def accept(self):
        from prog import valuedict
        try:
            name = self.e_name.text().strip()
            if len(name) == 0 or name[0] == '_':
                raise Exception("Invalid dictionary name")
            if name != self._ignore_name and name in self.projdict:
                raise Exception("{} dictionary already exists".format(name))
            tp = self.e_type.currentText()
            keys = self.e_table.model().get_keys()
            vals = self.e_table.model().get_values()
            comms = self.e_table.model().get_comms()
            self._ret_value = valuedict.Dictionary(name, tp,
                                                   keys, vals, comms)
            return super().accept()
        except Exception as e:
            qtcommon.message_exc(self, "Invalid input", e=e)

    def ret_value(self):
        return self._ret_value


# ========================== DictInformation
class DictInfoItem:
    def __init__(self, ditem=None, proj=None, newitem=None):
        self.used_by = collections.OrderedDict()
        if ditem is not None and proj is not None:
            self.olditem = ditem
            self.newitem = copy.deepcopy(ditem)
            # used by calculation
            for t in proj.data_tables:
                dt = []
                for c in t.columns.values():
                    if c.dt_type in ['BOOL', 'ENUM']:
                        if c.repr_delegate.dict is self.olditem:
                            dt.append(c.name)
                if len(dt) > 0:
                    self.used_by[t.table_name()] = dt
        elif newitem is not None:
            self.olditem = None
            self.newitem = newitem

    def uses_count(self):
        return sum([len(x) for x in self.used_by.values()])

    # Find removed dicts
    @classmethod
    def search_for_removed(cls, ditems, proj):
        """-> [(removed name, was it in use?)]
        """
        pdict = proj.dictionaries
        ret = []
        for oldname, olditem in pdict.items():
            vnew = next((x.newitem for x in ditems
                        if x.olditem.name == oldname), None)
            if vnew is None:
                dii = cls(olditem, proj)
                in_use = dii.uses_count() > 0
                ret.append((oldname, in_use))
        return ret

    @classmethod
    def search_for_changed(cls, ditems):
        """ -> [(changed name, new dict, was it shrinked?)]
        """
        ret = []
        for d in ditems:
            r = d.olditem.compare(d.newitem)
            if len(r) == 0:
                continue
            if 'keys removed' in r:
                ret.append((d.olditem.name, d.newitem, True))
            else:
                ret.append((d.olditem.name, d.newitem, False))
        return ret


class DictInfoFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.used_view = QtWidgets.QTextEdit()
        self.used_view.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.mapping_view = EditDictView(self)
        self.mapping_view.setFocusPolicy(QtCore.Qt.NoFocus)
        self.mapping_view.model().editable = False

        self.gb1 = QtWidgets.QGroupBox(self)
        self.gb1.setTitle("Used by")
        self.gb1.setLayout(QtWidgets.QHBoxLayout())
        self.gb1.layout().addWidget(self.used_view)
        self.gb1.setFixedHeight(180)
        self.gb2 = QtWidgets.QGroupBox(self)
        self.gb2.setTitle("Mapping")
        self.gb2.setLayout(QtWidgets.QHBoxLayout())
        self.gb2.layout().addWidget(self.mapping_view)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.gb1)
        self.layout().addWidget(self.gb2)

    def set_current_item(self, dictitem):
        self.mapping_view.model().reset_dict(dictitem.newitem)
        self.mapping_view.resizeColumnsToContents()
        self.used_view.clear()
        for tab, cols in dictitem.used_by.items():
            cnames = []
            for c in cols:
                cnames.append(c)
            line = "{}:  {}\n\n".format(tab, ', '.join(cnames))
            self.used_view.insertPlainText(line)


class DictTree(QtWidgets.QTreeWidget):
    ItemRole = QtCore.Qt.UserRole + 1
    item_changed = QtCore.pyqtSignal(DictInfoItem)

    def __init__(self, ditems, parent):
        super().__init__(parent)
        self.ditems = ditems
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.headerItem().setText(0, 'name')
        self.headerItem().setText(1, 'usage')
        self.itemDoubleClicked.connect(self._dclicked)
        self.setFixedWidth(180)
        self.init_fill()

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def selectionChanged(self, selected, deselected):   # noqa
        super().selectionChanged(selected, deselected)
        if len(selected.indexes()) > 0:
            d = selected.indexes()[0].data(self.ItemRole)
            self.item_changed.emit(d)

    def select_by_cap(self, cap):
        for it in range(self.topLevelItemCount()):
            t = self.topLevelItem(it)
            for ic in range(t.childCount()):
                c = t.child(ic)
                if cap is None or c.data(0, QtCore.Qt.DisplayRole) == cap:
                    c.setSelected(True)
                    return

    def init_fill(self):
        self.clear()
        itm1 = QtWidgets.QTreeWidgetItem(self)
        itm1.setData(0, QtCore.Qt.DisplayRole, "ENUM")
        itm1.setFlags(QtCore.Qt.ItemIsEnabled)
        for d in filter(lambda x: x.newitem.dt_type == "ENUM", self.ditems):
            itm = QtWidgets.QTreeWidgetItem(itm1)
            itm.setData(0, QtCore.Qt.DisplayRole, d.newitem.name)
            ucount = d.uses_count()
            if ucount > 0:
                itm.setData(1, QtCore.Qt.DisplayRole, str(ucount))
            itm.setData(0, self.ItemRole, d)
            itm.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

        itm2 = QtWidgets.QTreeWidgetItem(self)
        itm2.setData(0, QtCore.Qt.DisplayRole, "BOOL")
        itm2.setFlags(QtCore.Qt.ItemIsEnabled)
        for d in filter(lambda x: x.newitem.dt_type == "BOOL", self.ditems):
            itm = QtWidgets.QTreeWidgetItem(itm2)
            itm.setData(0, QtCore.Qt.DisplayRole, d.newitem.name)
            itm.setData(0, self.ItemRole, d)
            ucount = d.uses_count()
            if ucount > 0:
                itm.setData(1, QtCore.Qt.DisplayRole, str(ucount))
            itm.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        self.setColumnCount(2)
        self.expandAll()
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        menu = QtWidgets.QMenu(self)
        act_new = QtWidgets.QAction("New dictionary", self)
        act_new.triggered.connect(self._act_new)
        act_edit = QtWidgets.QAction("Edit", self)
        act_edit.triggered.connect(functools.partial(self._act_edit, index))
        act_rem = QtWidgets.QAction("Remove", self)
        act_rem.triggered.connect(functools.partial(self._act_rem, index))
        menu.addAction(act_edit)
        menu.addAction(act_rem)
        menu.addAction(act_new)
        if not index.isValid() or index.column() > 0:
            act_edit.setEnabled(False)
            act_rem.setEnabled(False)
        menu.popup(self.viewport().mapToGlobal(pnt))

    def _dclicked(self, item, column):
        if column == 0:
            index = self.indexFromItem(item)
            self._act_edit(index)

    def _act_new(self):
        d = {x.newitem.name: x.newitem for x in self.ditems}
        dialog = CreateNewDictionary(d, self)
        if dialog.exec_():
            nd = dialog.ret_value()
            self.ditems.append(DictInfoItem(newitem=nd))
            self.init_fill()

    def _act_rem(self, index):
        cap = index.data(QtCore.Qt.DisplayRole)
        for i, it in enumerate(self.ditems):
            if it.newitem.name == cap:
                self.ditems.pop(i)
                break
        self.init_fill()

    def _act_edit(self, index):
        cap = index.data(QtCore.Qt.DisplayRole)
        for it in self.ditems:
            if it.newitem.name == cap:
                break
        else:
            return
        d = {x.newitem.name: x.newitem for x in self.ditems}
        dialog = CreateNewDictionary(d, self)
        dialog.set_values_from(it.newitem)
        if dialog.exec_():
            nn = dialog.ret_value()
            it.newitem = nn
            self.init_fill()
            self.select_by_cap(None if nn is None else nn.name)


@qtcommon.hold_position
class DictInformation(dlgs.OkCancelDialog):
    def __init__(self, proj, parent):
        super().__init__("Dictionaries", parent, "horizontal")
        self.proj = proj
        self.ditems = []
        self._ret_value = None
        for v in proj.dictionaries.values():
            self.ditems.append(DictInfoItem(v, proj))

        # mainframe = qtree widget + right_frame
        self.tree = DictTree(self.ditems, self)
        self.right_frame = DictInfoFrame(self)
        self.mainframe.layout().addWidget(self.tree)
        self.mainframe.layout().addWidget(self.right_frame)

        # connect
        self.tree.item_changed.connect(self.right_frame.set_current_item)

    def accept(self):
        try:
            ret1, ret2 = {}, {'Shrink': False}
            # Find removed dicts
            # [(removed name, was it in use?)]
            rem_dicts = DictInfoItem.search_for_removed(self.ditems, self.proj)
            # [(changed name, new dict, was it shrinked?)]
            changed_dicts = DictInfoItem.search_for_changed(self.ditems)
            # removed
            ask_convert = False
            for a in rem_dicts:
                ret1[a[0]] = None
                if a[1]:
                    ask_convert = True
            # changed
            ask_shrink = False
            for a in changed_dicts:
                ret1[a[0]] = a[1]
                if a[2]:
                    ask_shrink = True
            if ask_convert:
                r = QtWidgets.QMessageBox.question(
                    self,
                    "Confirmation",
                    "Deleted dictionaries were used by "
                    "table data. Respective columns "
                    "will be converted to integers. Continue?",
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
                if r != QtWidgets.QMessageBox.Ok:
                    return
            if ask_shrink:
                r = QtWidgets.QMessageBox.question(
                    self,
                    "Confirmation",
                    "Some dictionary keys were removed. Would you like to "
                    "shrink respective column data to fit new dictionaries?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No |
                    QtWidgets.QMessageBox.Cancel)
                if r == QtWidgets.QMessageBox.Yes:
                    ret2['Shrink'] = True
                elif r == QtWidgets.QMessageBox.No:
                    ret2['Shrink'] = False
                else:
                    return
            self._ret_value = ret1, ret2
            super().accept()
        except Exception as e:
            qtcommon.message_exc(self, "Invalid input", e=e)

    def ret_value(self):
        """ -> {oldname -> new Dictionary},
               {'Shrink': bool}
        """
        return self._ret_value
