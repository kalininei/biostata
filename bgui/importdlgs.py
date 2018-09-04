import copy
from PyQt5 import QtWidgets, QtCore, QtGui
from bgui import optview
from bgui import optwdg
from bgui import dictdlg
from bgui import coloring
from bgui import dlgs
from fileproc import import_tab


class _ImportDialog(dlgs.OkCancelDialog):
    def __init__(self, proj, fn, parent):
        title = "Import table as {} from ({})".format(self.get_format(), fn)
        super().__init__(title, parent, "vertical")
        self._ret_value = None
        self.proj = proj
        self.fn = fn

        self.buttonbox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        # mainframe = upperframe + lowerframe
        self.mainframe.setLayout(QtWidgets.QVBoxLayout())
        self.upper_frame = QtWidgets.QFrame(self)
        self.lower_frame = QtWidgets.QFrame(self)
        self.mainframe.layout().addWidget(self.upper_frame)
        self.mainframe.layout().addWidget(self.lower_frame)
        self.mainframe.layout().setStretch(0, 2)
        self.mainframe.layout().setStretch(1, 2)

        # upper_frame = specific widget + load button
        self.upper_frame.setLayout(QtWidgets.QVBoxLayout())
        self.spec = self.specific_frame()
        self.upper_frame.layout().addWidget(self.spec)

        self.load_button = QtWidgets.QPushButton("Load")
        self.load_button.clicked.connect(self.do_load)
        self.load_button.setFixedWidth(80)
        self.upper_frame.layout().addWidget(
                self.load_button, 1, QtCore.Qt.AlignRight)

        # lower frame = table widget
        self.table = PreloadTable(self.proj, self)
        self.lower_frame.setLayout(QtWidgets.QVBoxLayout())
        self.lower_frame.layout().addWidget(self.table)

    def get_init_tabname(self):
        import os
        base = os.path.basename(self.fn)
        return os.path.splitext(base)[0]

    def load_table(self):
        raise NotImplementedError

    def do_load(self):
        try:
            self.load_table()
            self.buttonbox.button(
                    QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error",  str(e))

    def specific_frame(self):
        raise NotImplementedError

    def draw_table(self, caps, tab):
        self.table.load(caps, tab)

    def get_table_name(self):
        return self.spec.odata().tabname

    def accept(self):
        try:
            name = self.get_table_name()
            self.proj.is_valid_table_name(name)

            columns = self.table.model().get_columns()
            cnames = [c[0] for c in columns]
            for c in cnames:
                self.proj.is_possible_column_name(c)
            if len(set(cnames)) != len(cnames):
                raise Exception("Column names should be unique.")

            tab = self.table.model().get_tab()
            self._ret_value = name, tab, columns
            return super().accept()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Invalid Input",  str(e))

    def ret_value(self):
        '-> name, tab, columns'
        return self._ret_value


class PreloadModel(QtCore.QAbstractTableModel):
    format_changed = QtCore.pyqtSignal(int, str)

    def __init__(self, proj):
        super().__init__()
        self.proj = proj
        self.tab = []
        self.caps = []
        self.columns_enabled = []
        self.columns_format = []
        self.columns_dicts = []
        self.data_rows = 0
        self.data_columns = 0

    def load(self, caps, tab):
        self.beginResetModel()
        self.caps = caps if caps is not None else []
        self.tab = tab
        self.data_rows = len(self.tab)
        self.data_columns = max([len(x) for x in self.tab])
        if len(self.caps) < self.data_columns:
            nn = (self.data_columns - len(self.caps))
            self.caps = self.caps + [None]*nn
        self.columns_enabled = [True] * self.data_columns
        self.columns_format = ["TEXT"] * self.data_columns
        self.columns_dicts = [""] * self.data_columns

        for i, c in enumerate(self.caps):
            if not c:
                self.caps[i] = "Column {}".format(i)
        for i in range(self.data_columns):
            self.columns_format[i] = self.autodetect_type(i, 10)
        self.endResetModel()

    def autodetect_type(self, icol, maxsize):
        import ast
        r = "INT"  # 3-INT, 2-REAL, 1-TEXT
        for irow in range(min(maxsize, self.data_rows)):
            v = self.tab[irow][icol]
            if v is not "":
                try:
                    x = ast.literal_eval(v)
                    if type(x) is float:
                        r = "REAL"
                    elif type(x) is not int:
                        raise
                except:
                    return "TEXT"
        return r

    def columnCount(self, index=None):   # noqa
        return self.data_columns

    def rowCount(self, index=None):   # noqa
        return self.data_rows + 3

    def data(self, index, role):
        if not index.isValid():
            return None

        r, c = index.row(), index.column()
        if role == QtCore.Qt.DisplayRole:
            if r == 0:
                return self.caps[c]
            elif r == 1:
                return self.columns_format[c]
            elif r == 2:
                return self.columns_dicts[c]
            elif r > 2:
                v = self.tab[r-3][c]
                if self.columns_format[c] == "TEXT":
                    return v
                try:
                    if self.columns_format[c] == "INT":
                        return int(v)
                    elif self.columns_format[c] == "REAL":
                        return float(v)
                    elif self.columns_format[c] in ["BOOL", "ENUM"]:
                        dct = self.proj.get_dictionary(self.columns_dicts[c])
                        dct.value_to_key(v)
                        return v
                except Exception:
                    return None

        if role == QtCore.Qt.CheckStateRole:
            if r == 0:
                return QtCore.Qt.Checked if self.columns_enabled[c] else\
                        QtCore.Qt.Unchecked

        if role == QtCore.Qt.BackgroundRole:
            if r >= 3:
                col = QtGui.QColor(0, 0, 0, 0)
            else:
                col = coloring.get_bg2_color(0)
            if not (self.flags(index) & QtCore.Qt.ItemIsEnabled) or\
                    self.data(index, QtCore.Qt.DisplayRole) is None:
                col = QtGui.QColor(220, 220, 220)
            return QtGui.QBrush(col)

    def setData(self, index, value, role):  # noqa
        if not index.isValid():
            return None

        r, c = index.row(), index.column()
        if r == 0 and role == QtCore.Qt.CheckStateRole:
            v = value == QtCore.Qt.Checked
            self.columns_enabled[c] = v
            self.dataChanged.emit(index, self.createIndex(c, self.rowCount()))
        if role == QtCore.Qt.EditRole:
            if r == 0:
                try:
                    value = value.strip()
                    self.proj.is_possible_column_name(value)
                    self.caps[c] = value
                except:
                    return False
            if r == 1:
                self.columns_format[c] = value
                self.format_changed.emit(c, value)
            if r == 2:
                self.columns_dicts[c] = value
        return True

    def headerData(self, index, orient, role):   # noqa
        if orient == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                if index == 0:
                    return "Caption"
                elif index == 1:
                    return "Format"
                elif index == 2:
                    return "Dict"
                else:
                    return index - 2

    def flags(self, index):
        r, c = index.row(), index.column()
        if r > 0 and not self.columns_enabled[c]:
            return QtCore.Qt.NoItemFlags
        if r == 2 and self.columns_format[c] not in ["ENUM", "BOOL"]:
            return QtCore.Qt.NoItemFlags
        ret = QtCore.Qt.ItemIsEnabled
        if r < 3:
            ret = ret | QtCore.Qt.ItemIsEditable
        if r == 0:
            ret = ret | QtCore.Qt.ItemIsUserCheckable
        return ret

    def get_unique_data_values(self, icol):
        s = set([x[icol] for x in self.tab])
        return sorted(s)

    def get_columns(self):
        '-> [(name, type, dict), ... ]'
        ret = []
        for c in range(self.columnCount()):
            if self.columns_enabled[c]:
                ret.append((self.caps[c], self.columns_format[c],
                            self.columns_dicts[c]))
        return ret

    def get_tab(self):
        jreal = list(filter(lambda x: self.columns_enabled[x],
                            range(self.columnCount())))

        ret = [[None] * len(jreal) for _ in range(len(self.tab))]

        for j, jr in enumerate(jreal):
            if self.columns_format[jr] in ["ENUM", "BOOL"]:
                dct = self.proj.get_dictionary(self.columns_dicts[jr])
            else:
                dct = None
            for i in range(len(self.tab)):
                v = self.data(self.index(i + 3, jr), QtCore.Qt.DisplayRole)
                if v is not None and dct is not None:
                    v = dct.value_to_key(v)
                ret[i][j] = v
        return ret

    def mousePressEvent(self, event):   # noqa
        """ edit on single click """
        if event.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(event.pos())
            self.edit(index)
        super().mousePressEvent(event)


class ComboboxDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, values, parent):
        super().__init__(parent)
        self.set_values(values)

    def set_values(self, values):
        self.values = copy.deepcopy(values)

    def createEditor(self, parent, option, index):   # noqa
        ret = QtWidgets.QComboBox(parent)
        ret.addItems(self.values)
        return ret

    def setEditorData(self, editor, index):   # noqa
        editor.setCurrentText(index.data(QtCore.Qt.DisplayRole))

    def setModelData(self, editor, model, index):   # noqa
        model.setData(index, editor.currentText(), QtCore.Qt.EditRole)


class FormatComboboxDelegate(ComboboxDelegate):
    def __init__(self, parent):
        v = ["TEXT", "ENUM", "BOOL", "INT", "REAL"]
        super().__init__(v, parent)


class DictComboboxDelegate(ComboboxDelegate):
    def __init__(self, model,  parent):
        self.model = model
        super().__init__([], parent)

    def set_values(self, values):
        super().set_values(values)
        self.values.append("_ create new dict")

    def setModelData(self, editor, model, index):   # noqa
        value = editor.currentText()
        if value == '_ create new dict':
            c = index.column()
            uvals = self.model.get_unique_data_values(c)
            dialog = dictdlg.CreateNewDictionary(
                self.model.proj, self.parent(),
                self.model.columns_format[c], uvals, False)
            if dialog.exec_():
                dct = dialog.ret_value()
                self.model.proj.add_dictionary(dct)
                value = dct.name
            else:
                value = None
        if value:
            model.setData(index, value, QtCore.Qt.EditRole)


class PreloadTable(QtWidgets.QTableView):
    def __init__(self, proj, parent):
        super().__init__(parent)
        model = PreloadModel(proj)
        self.proj = proj
        self.setModel(model)
        self.format_delegate = FormatComboboxDelegate(self)
        self.dict_delegate = DictComboboxDelegate(self.model(), self)
        self.setItemDelegateForRow(1, self.format_delegate)
        self.setItemDelegateForRow(2, self.dict_delegate)
        self.model().format_changed.connect(self.format_changed)

    def format_changed(self, column, newformat):
        if newformat in ["ENUM", "BOOL"]:
            if newformat == "ENUM":
                posdicts = [x.name for x in self.proj.enum_dictionaries()]
            elif newformat == "BOOL":
                posdicts = [x.name for x in self.proj.bool_dictionaries()]
            if len(posdicts) == 0:
                posdicts = [""]
            self.dict_delegate.set_values(posdicts)
            self.model().setData(self.model().createIndex(2, column),
                                 posdicts[0], QtCore.Qt.EditRole)

    def load(self, caps, tab):
        self.model().load(caps, tab)
        self.resizeColumnsToContents()


class PlainTextOptions(QtWidgets.QFrame, optview.OptionsHolderInterface):
    def __init__(self, tabname, fname, parent):
        self.init_tabname = tabname
        self.init_fname = fname
        QtWidgets.QFrame.__init__(self, parent)
        optview.OptionsHolderInterface.__init__(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.oview)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.filename = ''
        obj.tabname = ''
        obj.firstline = 0
        obj.lastline = -1
        obj.read_cap = True
        obj.col_sep = "tab"
        obj.colcount = -1
        obj.row_sep = "newline"
        obj.ignore_blank = True
        obj.comment_sign = '#'

    def _odata_init(self):
        self.set_odata_entry("filename", self.init_fname)
        self.set_odata_entry("tabname", self.init_tabname)

    def olist(self):
        return optview.OptionsList([
            ("Import", "Filename", optwdg.OpenFileOptionEntry(
                self, "filename", [])),
            ("Import", "Table name", optwdg.SimpleOptionEntry(
                self, "tabname", dostrip=True)),
            ("Ranges", "First line", optwdg.BoundedIntOptionEntry(
                self, 'firstline', 0)),
            ("Ranges", "Last line", optwdg.BoundedIntOptionEntry(
                self, 'lastline', -1)),
            ("Ranges", "Caption from first row", optwdg.BoolOptionEntry(
                self, "read_cap")),
            ("Format", "Columns separator", optwdg.SingleChoiceEditOptionEntry(
                self, "col_sep", ["tab", "space", "any whitespace", ", ",
                                  "in double quotes"])),
            ("Format", "Max columns count", optwdg.BoundedIntOptionEntry(
                self, "colcount", -1)),
            ("Format", "Row separator", optwdg.SingleChoiceEditOptionEntry(
                self, "row_sep", ["newline", ";", "no (use column count)"])),
            ("Format", "Ignore empty lines", optwdg.BoolOptionEntry(
                self, "ignore_blank")),
            ("Format", "Comment sign", optwdg.SingleChoiceEditOptionEntry(
                self, "comment_sign", ["", "#", "//", "*"])),
            ])

    def ret_value(self):
        return copy.deepcopy(self.odata())

    def check_input(self):
        if not self.odata().filename:
            raise Exception("Invalid filename")


class ImportPlainText(_ImportDialog):
    _sz_x, _sz_y = 400, 500

    def __init__(self, proj, fname, parent):
        super().__init__(proj, fname, parent)

    def get_format(self):
        return "plain text"

    def specific_frame(self):
        return PlainTextOptions(self.get_init_tabname(), self.fn, self)

    def load_table(self):
        if self.spec.confirm_input():
            od = self.spec.ret_value()
            tab = import_tab.split_plain_text(od.filename, od)
            if od.read_cap:
                cap = tab[0]
                tab = tab[1:]
            else:
                cap = None
            self.draw_table(cap, tab)


class ImportXlsx(_ImportDialog):
    _sz_x, _sz_y = 400, 500

    def __init__(self, proj, fname, parent):
        super().__init__(proj, fname, parent)

    def get_format(self):
        return "Excel (xlsx)"

    def specific_frame(self):
        pass