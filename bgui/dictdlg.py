from PyQt5 import QtWidgets, QtCore
from bgui import dlgs
from bgui import qtcommon


class EditDictModel(QtCore.QAbstractTableModel):
    def __init__(self, uvals):
        super().__init__()
        self.mode = "ENUM"
        self.keys = [None] * 2
        self.values = [None] * 2
        self.comments = [None] * 2
        if uvals is not None:
            self.values = uvals[:]
            self.keys = list(range(len(uvals)))
            self.comments = [""] * len(uvals)

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

        if role == QtCore.Qt.DisplayRole:
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
        if not (self.mode == "BOOL" and index.column() == 0):
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
                self.values[index.row()] = value
            elif index.column() == 2:
                self.comments[index.row()] = value
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
        self.values = (self.values + [None] * n)[:n]
        self.comments = (self.comments + [None] * n)[:n]
        self.endResetModel()

    def autokeys(self):
        self.beginResetModel()
        self.keys = list(range(len(self.keys)))
        self.endResetModel()

    def get_keys(self):
        if self.mode == "BOOL":
            return [0, 1]
        else:
            return list(map(int, self.keys))

    def get_values(self):
        return list(map(str, self.values))

    def get_comms(self):
        return list(map(str, self.comments))


class EditDictView(QtWidgets.QTableView):
    def __init__(self, uvals, parent):
        super().__init__(parent)
        self.setModel(EditDictModel(uvals))
        self.verticalHeader().setVisible(False)


@qtcommon.hold_position
class CreateNewDictionary(dlgs.OkCancelDialog):
    def __init__(self, proj, parent, tp=None,
                 uvals=None, can_change_type=True):
        super().__init__("Create new dictionary", parent, "grid")
        resize(400, 300)
        self._ret_value = None
        self.proj = proj
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

        self.e_table = EditDictView(uvals, self)
        if tp is not None:
            self.e_table.model().set_mode(tp)
        self.e_type.currentTextChanged.connect(self.e_table.model().set_mode)
        self.e_spin.valueChanged.connect(self.e_table.model().set_length)
        self.autofill.clicked.connect(self.e_table.model().autokeys)
        self.mainframe.layout().addWidget(self.e_table, 4, 0, 1, 2)

        if tp is not None and not can_change_type:
            self.e_type.setEnabled(False)

    def get_autoname(self):
        i = 1
        while True:
            nm = "custom dictionary {}".format(i)
            if nm in self.proj.dictionaries:
                i += 1
            else:
                break
        return nm

    def accept(self):
        from bdata import projroot
        try:
            name = self.e_name.text()
            if name in self.proj.dictionaries:
                raise Exception("{} dictionary already exists".format(name))
            tp = self.e_type.currentText()
            keys = self.e_table.model().get_keys()
            vals = self.e_table.model().get_values()
            comms = self.e_table.model().get_comms()
            self._ret_value = projroot.Dictionary(name, tp,
                                                  keys, vals, comms)
            return super().accept()
        except Exception as e:
            qtcommon.message_exc(self, "Invalid input", e=e)

    def ret_value(self):
        return self._ret_value
