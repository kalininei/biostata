import collections
import functools
import copy
from PyQt5 import QtWidgets, QtCore, QtGui
from bdata import derived_tabs
from bdata import bcol
from bgui import qtcommon
from bgui import coloring
from bgui import dlgs
from prog import basic


@qtcommon.hold_position
class JoinTablesDialog(QtWidgets.QDialog):
    def __init__(self, dt, parent=None):
        super().__init__(parent)
        self.resize(700, 500)
        self.setWindowTitle("Join tables dialog")
        self.dt = dt
        # widget = mainframe/buttonbox
        self.setLayout(QtWidgets.QVBoxLayout())
        self.mainframe = QtWidgets.QFrame(self)
        self.buttonbox = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok |
                QtWidgets.QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.layout().addWidget(self.mainframe)
        self.layout().addWidget(self.buttonbox)
        # mainframe = left_frame/right_frame
        self.mainframe.setLayout(QtWidgets.QHBoxLayout())
        self.left_frame = QtWidgets.QFrame(self)
        self.left_frame.setMaximumWidth(150)
        self.right_frame = QtWidgets.QFrame(self)
        self.mainframe.layout().addWidget(self.left_frame)
        self.mainframe.layout().addWidget(self.right_frame)
        self.mainframe.layout().setStretch(0, 0)
        self.mainframe.layout().setStretch(1, 1)
        # left_frame = table_name + table_choice
        self.left_frame.setLayout(QtWidgets.QVBoxLayout())
        self.left_frame.layout().setContentsMargins(0, 0, 0, 0)
        self.e_tabname = QtWidgets.QLineEdit(self)
        self.e_tabchoice = TabChoice(self)
        self.left_frame.layout().addWidget(QtWidgets.QLabel(
            "New table name", self))
        self.left_frame.layout().addWidget(self.e_tabname)
        self.left_frame.layout().addWidget(QtWidgets.QLabel(
            "Join tables", self))
        self.left_frame.layout().addWidget(self.e_tabchoice)
        # right_frame = view columns + key columns
        self.right_frame.setLayout(QtWidgets.QVBoxLayout())
        self.right_frame.layout().setContentsMargins(0, 0, 0, 0)
        self.e_tabcols = TabColumnsChoiceFrame(self)
        self.e_tabkeys = TabKeysChoice(self)
        self.e_tabkeys.new_key_column.connect(self.e_tabcols.new_key_column)
        self.right_frame.layout().addWidget(QtWidgets.QLabel(
            "Columns passed to a new table"))
        self.right_frame.layout().addWidget(self.e_tabcols)
        self.right_frame.layout().addWidget(QtWidgets.QLabel("Key columns"))
        self.right_frame.layout().addWidget(self.e_tabkeys)
        # fill widgets
        self._init_fill()

    def _init_fill(self):
        # table name
        i = 1
        while True:
            nm = "Table {}".format(i)
            try:
                self.dt.proj.is_valid_table_name(nm)
                self.e_tabname.setText(nm)
                break
            except Exception:
                i += 1
        # connect table choice -> column choice
        self.e_tabchoice.itemChanged.connect(self._show_hide_table)

    def _show_hide_table(self, tab_choice_item):
        cs = tab_choice_item.checkState() == QtCore.Qt.Checked
        itab = tab_choice_item.data(TabChoice.TableIndexRole)
        self.e_tabcols.set_visible(itab, cs)
        self.e_tabkeys.set_visible(itab, cs)

    def assemble_ret_value(self):
        tabentries = []
        for tname in self.e_tabchoice.ret_value():
            te = derived_tabs.JoinTableEntry(tname)
            te.view_columns, te.name_columns = self.e_tabcols.ret_value(tname)
            te.key_columns, te.key_mappings = self.e_tabkeys.ret_value(tname)
            tabentries.append(te)

        self._ret_value = self.e_tabname.text().strip(), tabentries

    @staticmethod
    def _autorename(tabname, rv, colset):
        for i, v in enumerate(rv):
            if v in colset:
                rv[i] = v + " ({})".format(tabname)

    def check_input(self):
        # table count
        if len(self._ret_value[1]) < 2:
            raise Exception("At least two tables should be used")
        # table name
        self.dt.proj.is_valid_table_name(self._ret_value[0])
        # column names
        unique_colnames = set()
        notunique_colnames = set()
        for te in self._ret_value[1]:
            if len(te.name_columns) == 0:
                raise Exception('No columns were chosen '
                                'from table "{}".'.format(te.tabname))

            for c in te.name_columns:
                if c not in unique_colnames:
                    unique_colnames.add(c)
                else:
                    notunique_colnames.add(c)
        # non-unique columns
        if len(notunique_colnames) > 0:
            if len(notunique_colnames) > 1:
                c = 'Columns "{}" have ambiguous meaning. Make autorenaming?'
            else:
                c = 'Column "{}" has ambiguous meaning. Make autorenaming?'
            r = QtWidgets.QMessageBox.question(
                self, "Duplicated column names",
                c.format(", ".join(notunique_colnames)),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if r == QtWidgets.QMessageBox.Yes:
                for e in self._ret_value[1]:
                    self._autorename(
                        e.tabname, e.name_columns, notunique_colnames)
                return self.check_input()
            else:
                return False
        # valid columns names
        for c in unique_colnames:
            self.dt.proj.is_possible_column_name(c)
        # key columns
        numkeys = None
        for te in self._ret_value[1]:
            if numkeys is None:
                numkeys = len(te.key_columns)
            else:
                if numkeys == 0:
                    raise Exception("No key columns were chosen.")
                if numkeys != len(te.key_columns):
                    raise Exception("Key column counts differ.")
        return True

    def accept(self):
        try:
            self.assemble_ret_value()
            if self.check_input():
                super().accept()
        except Exception as e:
            qtcommon.message_exc(self, "Invalid input", e=e)

    def reject(self):
        super().reject()

    def ret_value(self):
        return self._ret_value


class TabChoice(QtWidgets.QListWidget):
    TableIndexRole = QtCore.Qt.UserRole + 1

    def __init__(self, dlg):
        super().__init__(dlg)
        # table choice
        for i, tab in enumerate(dlg.dt.proj.data_tables):
            itm = QtWidgets.QListWidgetItem(tab.table_name())
            itm.setCheckState(QtCore.Qt.Unchecked)
            itm.setData(TabChoice.TableIndexRole, i)
            self.addItem(itm)

    def ret_value(self):
        ret = []
        for i in range(self.count()):
            itm = self.item(i)
            if itm.checkState() == QtCore.Qt.Checked:
                ret.append(itm.text())
        return ret


class TabColumnsChoiceFrame(QtWidgets.QFrame):
    def __init__(self, dlg):
        super().__init__(dlg)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        container = QtWidgets.QWidget(self)
        container.setLayout(QtWidgets.QHBoxLayout())
        container.layout().setSpacing(0)
        self.tabs = []
        for t in dlg.dt.proj.data_tables:
            self.tabs.append(TabColumnsChoice(t, container))
        for t in self.tabs:
            container.layout().addWidget(t)
            t.setVisible(False)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.layout().addWidget(scroll)

    def set_visible(self, itab, doshow):
        self.tabs[itab].setVisible(doshow)

    def ret_value(self, tabname):
        """ [orig column names], [join names] """
        r1, r2 = [], []
        t = next(x for x in self.tabs if x.title() == tabname)
        for i in range(t.wtab.rowCount()):
            itm = t.wtab.item(i, 0)
            if itm.checkState() == QtCore.Qt.Checked:
                r1.append(t.wtab.item(i, 0).text())
                r2.append(t.wtab.item(i, 2).text().strip())
        return r1, r2

    def new_key_column(self, itab, igroup, colname):
        if colname is not None:
            self.tabs[itab].reset_color_group(igroup, colname)
        else:
            self.tabs[itab].remove_color_group(igroup)


class TabColumnsChoice(QtWidgets.QGroupBox):
    def __init__(self, tab, parent):
        super().__init__(parent)
        self.setTitle(tab.table_name())
        self.setLayout(QtWidgets.QVBoxLayout())
        self.wtab = QtWidgets.QTableWidget(self)
        self.wtab.setRowCount(len(tab.all_columns))
        self.wtab.setColumnCount(3)
        # zero margins
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setFlat(True)
        for i, c in enumerate(tab.all_columns):
            itm1 = QtWidgets.QTableWidgetItem(c.name)
            itm1.setCheckState(QtCore.Qt.Unchecked)
            itm2 = QtWidgets.QTableWidgetItem(c.col_type())
            nn = c.name
            if nn == 'id':
                nn = 'id ({})'.format(tab.table_name())
            itm3 = QtWidgets.QTableWidgetItem(nn)
            itm1.setFlags(QtCore.Qt.ItemIsEnabled |
                          QtCore.Qt.ItemIsUserCheckable)
            itm2.setFlags(QtCore.Qt.ItemIsEnabled)
            itm3.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
            self.wtab.setItem(i, 0, itm1)
            self.wtab.setItem(i, 1, itm2)
            self.wtab.setItem(i, 2, itm3)
        self.layout().addWidget(self.wtab)
        self.wtab.horizontalHeader().setTextElideMode(QtCore.Qt.ElideRight)
        hitm = map(QtWidgets.QTableWidgetItem,
                   ["name", "type", "name in join table"])
        for i, itm in enumerate(hitm):
            self.wtab.setHorizontalHeaderItem(i, itm)
            self.wtab.horizontalHeader().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeToContents)
        # fixed size table
        self.wtab.verticalHeader().setVisible(False)
        self.adjust_size()
        self.wtab.itemChanged.connect(self.adjust_size)
        # color groups
        self.color_group = [-1] * len(tab.all_columns)

    def adjust_size(self, itm=None):
        self.wtab.setMinimumWidth(self.wtab.horizontalHeader().length()+5)
        self.setMinimumWidth(self.wtab.horizontalHeader().length()+5)
        self.wtab.setMinimumHeight(self.wtab.verticalHeader().length()+100)
        self.setMinimumHeight(self.wtab.verticalHeader().length()+100)

    def remove_color_group(self, igroup, do_reset=True):
        for i, c in enumerate(self.color_group):
            if c == igroup:
                self.color_group[i] = -1
        if do_reset:
            self._reset_colors()

    def reset_color_group(self, igroup, colname):
        self.remove_color_group(igroup, False)
        for i in range(self.wtab.rowCount()):
            if self.wtab.item(i, 0).text() == colname:
                self.color_group[i] = igroup
                break
        self._reset_colors()

    def _reset_colors(self):
        for i, cg in enumerate(self.color_group):
            for j in range(self.wtab.columnCount()):
                if cg > -1:
                    col = coloring.get_group_color_light(cg)
                else:
                    col = QtGui.QColor(0, 0, 0, 0)
                self.wtab.item(i, j).setBackground(col)
        self.wtab.reset()


class TabKeysRow:
    def __init__(self, proj, irow, parent):
        self.is_dead = False
        self.parent = parent
        self.proj = proj
        self.wid = []
        self.irow = irow
        for i, t in enumerate(proj.data_tables):
            self.wid.append(QtWidgets.QComboBox(parent))
            for col in t.all_columns:
                self.wid[-1].addItem(col.name)
            self.wid[-1].setVisible(parent.visibility[i])
            self.wid[-1].addItem('')
            self.wid[-1].setCurrentText('')
            self.wid[-1].currentIndexChanged.connect(
                    functools.partial(self.index_changed, i))
        self.wid.append(QtWidgets.QLabel(parent))
        self.wid.append(QtWidgets.QPushButton(parent))
        self.wid.append(QtWidgets.QPushButton(parent))
        self.wid.append(QtWidgets.QPushButton(parent))
        # key columns (combobox)
        self.cb_col = self.wid[:-4]
        # warning label (label)
        self.w_label = self.wid[-4]
        # buttons: link, remove, new row
        self.b_link = self.wid[-3]
        self.b_rem = self.wid[-2]
        self.b_add = self.wid[-1]
        self.w_label.setToolTip("Non-trivial mapping")
        self.w_label.setPixmap(QtGui.QPixmap(":/warning"))
        self.w_label.setVisible(False)
        self.w_label.setScaledContents(True)
        self.w_label.setMaximumWidth(20)
        self.w_label.setMaximumHeight(20)
        self.b_link.setFixedWidth(30)
        self.b_link.setIcon(QtGui.QIcon(":/link"))
        self.b_link.setEnabled(False)
        self.b_link.clicked.connect(self.edit_mapping)
        self.b_link.setToolTip("Edit column data mappings")
        self.b_rem.setFixedWidth(30)
        self.b_rem.setIcon(QtGui.QIcon(":/remove"))
        self.b_rem.clicked.connect(self.remove)
        self.b_rem.setEnabled(False)
        self.b_rem.setToolTip("Remove this line")
        self.b_add.setFixedWidth(30)
        self.b_add.setIcon(QtGui.QIcon(":/new-row"))
        self.b_add.setEnabled(True)
        self.b_add.clicked.connect(self.add_row)
        self.b_add.setToolTip("Append key columns set")

        cbframe = QtWidgets.QWidget()
        cbframe.setLayout(QtWidgets.QHBoxLayout())
        cbframe.layout().setContentsMargins(0, 0, 0, 0)
        for w in self.cb_col:
            cbframe.layout().addWidget(w)
        parent.layout().addWidget(cbframe, irow, 0)
        parent.layout().addWidget(self.w_label, irow, 1)
        parent.layout().addWidget(self.b_link, irow, 2)
        parent.layout().addWidget(self.b_rem, irow, 3)
        parent.layout().addWidget(self.b_add, irow, 4)

        for j, w in enumerate(self.wid):
            w.setFocusPolicy(QtCore.Qt.NoFocus)
        # {i_table: {key_value: group_code} }
        self.mapping = {}
        self.can_use_simple_mapping = False

    def remove(self):
        self.is_dead = True
        for w in self.wid:
            w.setEnabled(False)
            w.setVisible(False)
        for i in range(len(self.proj.data_tables)):
            self.parent.new_key_column.emit(i, self.irow, None)

    def add_row(self):
        if self.parent.is_last_row(self.irow):
            self.parent.add_row()
            self.b_rem.setEnabled(True)

    def set_visible(self, itab, cs):
        if not self.is_dead:
            self.wid[itab].setVisible(cs)
            txt = self.cb_col[itab].currentText() if cs else ''
            self.parent.new_key_column.emit(itab, self.irow, txt)

    def index_changed(self, ntab, ind):
        self.b_link.setEnabled(self.has_all_data())
        self.parent.new_key_column.emit(
                ntab, self.irow, self.cb_col[ntab].currentText())
        self.can_use_simple_mapping = True
        if self.has_all_data():
            # if all columns are same we can use simple mapping
            itabs = [i for i, x in enumerate(self.cb_col) if x.isVisible()]
            colnames = [self.wid[itab].currentText() for itab in itabs]
            tabs = [self.proj.data_tables[itab] for itab in itabs]
            cols = [t.get_column(c) for t, c in zip(tabs, colnames)]
            self.can_use_simple_mapping = bcol.ColumnInfo.are_same(cols)
            self.init_mapping()
        self.set_warning()

    def set_warning(self):
        # warning sign if we use non-trivial mapping
        self.w_label.setVisible(self.has_all_data() and bool(self.mapping))

    def init_mapping(self):
        if self.can_use_simple_mapping:
            self.mapping = {}
        else:
            itabs = [i for i, x in enumerate(self.cb_col) if x.isVisible()]
            tabs = [self.proj.data_tables[x] for x in itabs]
            cols = [tabs[x].get_column(self.wid[x].currentText())
                    for x in itabs]
            im = prebuild_mapping(tabs, cols)
            for i, m in zip(itabs, im):
                self.mapping[i] = m

    def has_all_data(self):
        if len(self.wid) < 4:
            return False
        for w in self.cb_col:
            if w.isVisible() and not w.currentText():
                return False
        return True

    def is_active(self):
        return (self.has_all_data() and not self.is_dead)

    def get_colname(self, table_index):
        return self.wid[table_index].currentText()

    def get_mapping(self, table_index):
        try:
            d = self.mapping[table_index]
            return lambda x: d[x]
        except KeyError:
            return lambda x: x

    def edit_mapping(self):
        itabs = [i for i, w in enumerate(self.cb_col) if w.isVisible()]
        # assemble used tabels, columns and column captions
        tables, columns, captions = [], [], []
        for itab in itabs:
            tables.append(self.proj.data_tables[itab])
            cn = self.wid[itab].currentText()
            columns.append(self.proj.data_tables[itab].get_column(cn))
            cap = columns[-1].name
            tname = self.proj.data_tables[itab].table_name()
            if cap.find(tname) < 0:
                cap += " ({})".format(tname)
            captions.append(cap)
        # assemble used mappings or None
        try:
            maps = [self.mapping[i] for i in itabs]
        except KeyError:
            maps = None
        assert (maps is not None) or (self.can_use_simple_mapping)
        dialog = EditMappingsDialog(tables, columns, captions, maps,
                                    self.can_use_simple_mapping, self.parent)
        if dialog.exec_():
            maps = dialog.ret_value()
            if maps is not None:
                for i, itab in enumerate(itabs):
                    self.mapping[itab] = maps[i]
            else:
                assert self.can_use_simple_mapping
                self.mapping.clear()
            self.set_warning()


class TabKeysChoice(QtWidgets.QFrame):
    # ntable, nset, column name
    new_key_column = QtCore.pyqtSignal(int, int, str)

    def __init__(self, dlg):
        self.proj = dlg.dt.proj
        super().__init__(dlg)
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        # visibility
        self.visibility = [False] * len(self.proj.data_tables)
        # caption
        self.caps = []
        caps_widget = QtWidgets.QWidget(self)
        caps_widget.setLayout(QtWidgets.QHBoxLayout())
        caps_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(caps_widget, 0, 0)
        for i, t in enumerate(self.proj.data_tables):
            self.caps.append(QtWidgets.QLabel(t.table_name()))
            caps_widget.layout().addWidget(self.caps[-1])
            self.caps[-1].setVisible(False)
            self.caps[-1].setAlignment(QtCore.Qt.AlignHCenter)
        # frows
        self.frows = []
        self.add_row()

    def add_row(self):
        for f in self.frows:
            f.b_add.setVisible(False)
        self.frows.append(TabKeysRow(self.proj, len(self.frows)+1, self))

    def set_visible(self, itab, cs):
        self.visibility[itab] = cs
        self.caps[itab].setVisible(cs)
        for f in self.frows:
            f.set_visible(itab, cs)

    def is_last_row(self, irow):
        return irow > len(self.frows) - 1

    def ret_value(self, tname):
        """ -> [key columns], [key mappings]"""
        r1, r2 = [], []
        tindex = next(i for i, t in enumerate(self.proj.data_tables)
                      if t.name == tname)
        for f in filter(lambda x: x.is_active(), self.frows):
            r1.append(f.get_colname(tindex))
            r2.append(f.get_mapping(tindex))
        return r1, r2


class EditMappingsModel(QtCore.QAbstractTableModel):
    GroupRole = QtCore.Qt.UserRole + 1
    ColumnNameRole = QtCore.Qt.UserRole + 2
    DataRole = QtCore.Qt.UserRole + 3
    repr_updated = QtCore.pyqtSignal()
    bgcolor1 = QtGui.QColor(255, 255, 0, 70)
    bgcolor2 = QtGui.QColor(255, 255, 0, 40)

    def __init__(self, data, columns, names):
        super().__init__()
        self.groups = copy.deepcopy(data)
        # set Nones
        for a in self.groups:
            for b in a:
                for i in range(len(b)):
                    if b[i] is None:
                        b[i] = basic.CustomNone()
        self.names = copy.deepcopy(names)
        self.columns = columns
        self.totrows = []
        self._reset_data()
        self.__drag_index = QtCore.QModelIndex()

    def rowCount(self, index=None):   # noqa
        return len(self.totrows)

    def columnCount(self, index=None):  # noqa
        return len(self.totrows[0])

    def spans(self):
        sp = [[] for _ in self.groups]
        for irow, ig in [(x, self.totrows[x][0])
                         for x in range(self.rowCount())]:
            sp[ig].append(irow)
        return [[min(x), max(x)] for x in sp if len(x) > 1]

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == EditMappingsModel.DataRole:
            v = self.totrows[index.row()][index.column()]
            if v is not None and index.column() >= 1:
                col = self.columns[index.column() - 1]
                if col.dt_type == "BOOL":
                    v = "{} ({})".format(col.repr(v), True if v else False)
                elif col.dt_type == "ENUM":
                    v = col.repr(v)
            if v == '':
                return basic.CustomEString()
            return v
        elif role == QtCore.Qt.DisplayRole:
            v = self.data(index, EditMappingsModel.DataRole)
            if isinstance(v, basic.CustomObject):
                return str(v)
            else:
                return v
        elif role == EditMappingsModel.GroupRole:
            return self.totrows[index.row()][0]
        elif role == EditMappingsModel.ColumnNameRole:
            return list(self.groups[0].keys())[index.column()-1]
        elif role == QtCore.Qt.BackgroundRole:
            if index.row() == self.rowCount() - 1:
                c = QtGui.QColor(255, 255, 255)
            elif self.totrows[index.row()][0] % 2:
                c = self.bgcolor1
            else:
                c = self.bgcolor2
            return QtGui.QBrush(c)
        elif role == QtCore.Qt.ForegroundRole:
            v = self.data(index, EditMappingsModel.DataRole)
            if isinstance(v, basic.CustomObject):
                return QtGui.QBrush(QtGui.QColor(200, 200, 200))
            else:
                return None
        return None

    def set_drag_group(self, index):
        self.__drag_index = index

    def headerData(self, ind, orient, role):   # noqa
        if role == QtCore.Qt.DisplayRole:
            if orient == QtCore.Qt.Horizontal:
                if ind == 0:
                    return "GroupID"
                else:
                    return self.names[ind-1]
        return super().headerData(ind, orient, role)

    def flags(self, index):   # noqa
        ret = QtCore.Qt.ItemIsEnabled
        if index.column() >= 1:
            if self.data(index, EditMappingsModel.DataRole) is not None:
                ret = ret | QtCore.Qt.ItemIsSelectable
                ret = ret | QtCore.Qt.ItemIsDragEnabled
        g1 = self.data(self.__drag_index, EditMappingsModel.GroupRole)
        if g1 is not None:
            g2 = self.data(index, EditMappingsModel.GroupRole)
            if g1 != g2:
                ret = ret | QtCore.Qt.ItemIsDropEnabled
        return ret

    def _adjust_groups(self):
        # remove empty groups
        rm = []
        for i, g in enumerate(self.groups):
            has_data = False
            for val in g:
                if len(val) > 0:
                    has_data = True
                    break
            if not has_data:
                rm.append(i)
        for i in reversed(rm):
            self.groups.pop(i)
        # add empty row to the end
        if len(self.groups) > 0:
            eg = copy.deepcopy(self.groups[0])
            for v in eg:
                v.clear()
            self.groups.append(eg)

    def _reset_data(self):
        self._adjust_groups()
        self.totrows = []
        for igr, gr in enumerate(self.groups):
            nrows = max(1, max([len(x) for x in gr]))
            ncols = len(gr) + 1
            rows = [[None for _ in range(ncols)] for _ in range(nrows)]
            for i in range(nrows):
                rows[i][0] = igr
            for itab,  row_values in enumerate(gr):
                for i,  v in enumerate(row_values):
                    rows[i][itab+1] = v
            self.totrows.extend(rows)
        self.repr_updated.emit()

    def dropMimeData(self, data, action, row, column, parent):   # noqa
        if not parent.isValid():
            return 0
        self.beginResetModel()
        oldgroup = self.data(self.__drag_index, EditMappingsModel.GroupRole)
        newgroup = self.data(parent, EditMappingsModel.GroupRole)
        r, c = self.__drag_index.row(), self.__drag_index.column()
        dt = self.totrows[r][c]
        # 1. add to new group
        self.groups[newgroup][c-1].append(dt)
        # 2. remove from old group
        self.groups[oldgroup][c-1].remove(dt)
        # 3. reset
        self._reset_data()
        self.__drag_index = QtCore.QModelIndex()
        self.endResetModel()
        return 0

    def supportedDropActions(self):   # noqa
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction


class EditMappingsTable(QtWidgets.QTableView):
    def __init__(self, names, parent):
        super().__init__(parent)
        self.names = names
        self.columns = parent.columns
        # captions
        self.verticalHeader().setVisible(False)
        # selection behaiviour:
        self.setSelectionMode(
                QtWidgets.QAbstractItemView.SingleSelection)
        # drag drop
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

    def init_groups(self, groups):
        assert self.model() is None

        self.setModel(EditMappingsModel(groups, self.columns, self.names))
        self.model().repr_updated.connect(self.updated)
        self.updated()

    def startDrag(self, action):   # noqa
        ind = self.selectionModel().currentIndex()
        # allow moves only within current group
        self.model().set_drag_group(ind)
        super().startDrag(action)

    def updated(self):
        self.clearSpans()
        for s in self.model().spans():
            self.setSpan(s[0], 0, s[1]-s[0]+1, 1)

    def ret_value(self):
        if self.model() is None:
            return None
        ret = copy.deepcopy(self.model().groups)
        # set from Nones
        for a in ret:
            for b in a:
                for i in range(len(b)):
                    if isinstance(b[i], basic.CustomNone):
                        b[i] = None
        return ret


@qtcommon.hold_position
class EditMappingsDialog(dlgs.OkCancelDialog):
    def __init__(self, tables, columns, captions, maps,
                 can_use_simple_mapping, parent):
        super().__init__("Edit column mappings", parent, "vertical")
        self.resize(300, 400)
        # fill table widget
        self.columns = columns
        self.tables = tables
        # [group index][table index] -> [list of possible column values]
        self.groups = []
        self.__groups_initialized = False
        # mainframe = value-to-value checkbox, QTableWidget
        self.vtv = QtWidgets.QCheckBox("Value-to-value mapping")
        self.vtv.setChecked(maps is None)
        self.vtv.setEnabled(can_use_simple_mapping)
        self.vtv.toggled.connect(self.vtv_toggled)
        # main table
        self.tab = EditMappingsTable(captions, self)
        self.tab.setEnabled(maps is not None)
        self.mainframe.layout().addWidget(self.vtv)
        self.mainframe.layout().addWidget(self.tab)
        # initialize edit table
        if maps is not None:
            self.init_fill(maps)

    def init_fill(self, maps=None):
        if self.__groups_initialized:
            return
        self.__groups_initialized = True
        # init mappings -> groups
        if maps is None:
            maps = prebuild_mapping(self.tables, self.columns)
        ngroups = 0
        for e in maps:
            ngroups = max(ngroups, max(e.values()))
        ngroups += 1
        ncols = len(self.columns)
        self.groups.clear()
        for i in range(ngroups):
            self.groups.append([[] for j in range(ncols)])
        for itab, d in enumerate(maps):
            for key, gr_code in d.items():
                self.groups[gr_code][itab].append(key)
        self.tab.init_groups(self.groups)

    def vtv_toggled(self, status):
        if not status:
            self.init_fill()
        self.tab.setEnabled(not status)

    def ret_value(self):
        # simple mapping was used
        if self.vtv.isChecked():
            return None
        # groups -> mappings
        self.groups = self.tab.ret_value()
        maps = [{} for _ in range(len(self.columns))]
        for gr_code, gr in enumerate(self.groups):
            for itab, vals in enumerate(gr):
                for val in vals:
                    maps[itab][val] = gr_code
        return maps


def prebuild_mapping(tabs, columns):
    # assemble possible values
    # -> (key value, representation value)
    possible_values = []
    for tab, col in zip(tabs, columns):
        if col.dt_type in ["ENUM", "BOOL"]:
            pv1 = col.repr_delegate.dict.keys()
        else:
            pv1 = tab.get_distinct_column_raw_vals(col.name, False, True)
        possible_values.append(pv1)
    # apply
    ret = []
    for pv in possible_values:
        ret.append(collections.OrderedDict(
            [(x, j) for j, x in enumerate(pv)]))

    # resort possible values
    keys = []
    for i, r in enumerate(ret):
        col = columns[i]
        for v in r.keys():
            a = col.repr(v)
            try:
                k = keys.index(a)
                r[v] = k
            except ValueError:
                keys.append(a)
                r[v] = len(keys) - 1
    return ret
