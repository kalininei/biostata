#!/usr/bin/env python3
import copy
from PyQt5 import QtWidgets, QtCore
from bgui import qtcommon
from bgui import dlgs
from bdata import filt


class FilterRow:
    def __init__(self, dlg, irow):
        self.dlg = dlg
        self._ret_value = None
        # 0 - concat, 1 - left paren, 2 - target,
        # 3 - action, 4 - value 5 - right paren
        self.cb = [QtWidgets.QComboBox(dlg.ff) for _ in range(6)]
        self.cb[4].setEditable(True)
        self.columns = list(dlg.datatab.columns.values())
        self.current_column = 0
        self.current_action = 0

        self.cb[0].addItems(filt.fconcat + ["- remove"])
        self.cb[1].addItems(filt.fopenparen)
        self.cb[2].addItems(['"{}"'.format(x.name) for x in self.columns])
        self.cb[5].addItems(filt.fcloseparen)

        for i, c in enumerate(self.cb):
            c.setEnabled(False)
            dlg.ff.layout().addWidget(c, irow, i)
            c.setCurrentIndex(-1)
            c.setFocusPolicy(QtCore.Qt.NoFocus)
        self.cb[4].setFocusPolicy(QtCore.Qt.StrongFocus)

        self.cb[0].currentIndexChanged.connect(self._activate)
        self.cb[2].currentIndexChanged.connect(self._target_changed)
        self.cb[3].currentIndexChanged.connect(self._action_changed)

        self._enabled = False
        self.cb[0].setEnabled(True)

    def is_enabled(self):
        return self._enabled

    def _activate(self, i=0):
        if not self.is_enabled() and self.cb[0].currentText() != "- remove":
            self._enabled = True
            for c in self.cb:
                c.setEnabled(True)
            self.cb[2].setCurrentIndex(0)
            self.dlg._update_filter_entries()
        elif self.cb[0].currentText() == "- remove":
            for c in self.cb:
                c.setHidden(True)
            self.dlg.frows.remove(self)
            self.dlg._update_filter_entries()

    def _target_changed(self, i):
        self.current_column = self.columns[i]
        self.cb[3].clear()
        self.cb[3].addItems(filt.factions(self.columns[i].dt_type))
        self.cb[3].setCurrentIndex(-1)
        self.cb[4].setCurrentIndex(-1)
        if self.current_column.dt_type in ["BOOL", "ENUM"]:
            self.cb[4].setEditable(False)
        else:
            self.cb[4].setEditable(True)
        self.cb[3].setCurrentIndex(0)

    def _action_changed(self, i):
        self.current_action = self.cb[3].itemText(i)
        if self.current_action in ["NULL", "not NULL"]:
            self.cb[4].setEnabled(False)
        else:
            self.cb[4].setEnabled(True)
            self.cb[4].clear()
            self.cb[4].addItems(filt.possible_values_list(
                self.current_column, self.current_action, self.dlg.datatab))
            if self.cb[4].isEditable():
                self.cb[4].setCurrentIndex(-1)
            else:
                self.cb[4].setCurrentIndex(0)

    def get_column(self):
        return self.columns[self.cb[2].currentIndex()]

    def fill_from_entry(self, e):
        self._activate()
        self.cb[0].setCurrentText(e.concat)
        self.cb[1].setCurrentText(e.paren1)
        self.cb[2].setCurrentText('"'+e.column.name+'"')
        self.cb[3].setCurrentText(e.action)
        if isinstance(e.value, filt.ColumnDef):
            self.cb[4].setCurrentText('"' + e.value.name + '"')
        elif e.action == "one of":
            self.cb[4].setCurrentText(",".join(map(str, e.value)))
        else:
            col = self.dlg.datatab.columns[e.column.name]
            self.cb[4].setCurrentText(str(col.repr(e.value)))
        self.cb[5].setCurrentText(e.paren2)


@qtcommon.hold_position
class EditFilterDialog(dlgs.OkCancelDialog):
    def __init__(self, filt, datatab, used_names, parent):
        super().__init__("Edit filter", parent, "vertical")
        self.resize(300, 400)
        self.__deactivate_update_filter_entries = False
        self.__last_frow = -1
        if used_names is None:
            self.used_names = [x.name for x in datatab.proj.named_filters]
        else:
            self.used_names = copy.deepcopy(used_names)
        # if this is edit dialog we allow new filter to have the name
        # the old one
        if filt is not None and filt.name in self.used_names:
            self.used_names.remove(filt.name)
        self.datatab = datatab
        self.frows = []
        self._add_nameframe(filt, self.mainframe)
        self._add_filterframe(filt, self.mainframe)
        self.mainframe.layout().addStretch(1)

    def named_filter_next_name(self):
        i = 1
        while True:
            nm = "Filter {}".format(i)
            if nm in self.used_names:
                i += 1
            else:
                return nm

    def _add_nameframe(self, filt, parent):
        frame = QtWidgets.QFrame(parent)
        frame.setLayout(QtWidgets.QHBoxLayout())
        frame.layout().setContentsMargins(0, 0, 0, 0)
        parent.layout().addWidget(frame)
        parent.layout().setStretch(0, 0)

        gb = QtWidgets.QGroupBox(frame)
        gb.setTitle("Filter name")
        gb.setLayout(QtWidgets.QVBoxLayout())
        chw = QtWidgets.QCheckBox(gb)
        chw.setText("Anonymous")
        edw = QtWidgets.QLineEdit(gb)
        edw.setText(self.named_filter_next_name())
        chw.toggled.connect(lambda x: edw.setEnabled(not x))
        chw.setChecked(True)
        gb.layout().addWidget(chw)
        gb.layout().addWidget(edw)
        if filt is not None:
            chw.setChecked(not bool(filt.name))
            if filt.name:
                edw.setText(filt.name)
        self.filter_name = edw
        self.filter_cb = chw
        frame.layout().addWidget(gb)

        gb = QtWidgets.QGroupBox(frame)
        gb.setTitle("Filter type")
        gb.setLayout(QtWidgets.QVBoxLayout())
        cb = QtWidgets.QComboBox(gb)
        cb.addItems(["Remove", "Leave only"])
        gb.layout().addWidget(QtWidgets.QLabel())
        gb.layout().addWidget(cb)
        parent.layout().addWidget(gb)
        parent.layout().setStretch(1, 0)
        if filt is not None:
            if filt.do_remove:
                cb.setCurrentIndex(0)
            else:
                cb.setCurrentIndex(1)
        self.filter_type = cb
        frame.layout().addWidget(gb)

        frame.layout().setStretch(0, 1)
        frame.layout().setStretch(1, 1)

    def _add_filterframe(self, filt, parent):
        self.ff = QtWidgets.QGroupBox(parent)
        parent.layout().addWidget(self.ff)
        parent.layout().setStretch(1, 0)
        self.ff.setTitle("Filter definition")
        self.ff.setLayout(QtWidgets.QGridLayout())
        self.ff.layout().setColumnStretch(0, 0)
        self.ff.layout().setColumnStretch(1, 0)
        self.ff.layout().setColumnStretch(2, 1)
        self.ff.layout().setColumnStretch(3, 0)
        self.ff.layout().setColumnStretch(4, 2)
        self.ff.layout().setColumnStretch(5, 0)
        self.__deactivate_update_filter_entries = True
        if filt is not None:
            for e in filt.entries:
                self._add_filterframe_row(e)
        else:
            self._add_filterframe_row(None)
        self.__deactivate_update_filter_entries = False
        self._update_filter_entries()

    def _add_filterframe_row(self, e):
        self.__last_frow += 1
        frame = FilterRow(self, self.__last_frow)
        self.frows.append(frame)
        if e is not None:
            frame.fill_from_entry(e)

    def _update_filter_entries(self):
        if self.__deactivate_update_filter_entries:
            return
        # hide left top checkbox
        self.frows[0].cb[0].setHidden(True)
        if not self.frows[0].is_enabled():
            self.frows[0]._activate()
        # add last line
        if self.frows[-1].is_enabled():
            self._add_filterframe_row(None)

    def _check_input(self):
        # 1) parenthesis
        x = 0
        for f in self.frows[:-1]:
            x += f.cb[1].currentText().count('(')
            if f.cb[5].currentText() == ')...)':
                x = 0
            else:
                x -= f.cb[5].currentText().count(')')
        if x != 0:
            raise Exception("Check parenthesis")
        # 2) unique name
        if self.filter_name.isEnabled():
            if self.filter_name.text() in self.used_names:
                raise Exception("Filter name already exists")

    def _assemble_return(self):
        ret = filt.Filter()
        # name
        if self.filter_name.isEnabled():
            ret.name = self.filter_name.text()
        # type
        ret.do_remove = self.filter_type.currentText() == "Remove"
        # rows
        for f in self.frows[:-1]:
            e = filt.FilterEntry()
            e.concat = f.cb[0].currentText()
            e.paren1 = f.cb[1].currentText()
            e.paren2 = f.cb[5].currentText()
            ecol = f.get_column()
            e.column = filt.ColumnDef.from_column(ecol)
            e.action = f.cb[3].currentText()
            # value interpretation
            if e.action not in ["NULL", "not NULL"]:
                atxt = f.cb[4].currentText()
                if atxt.startswith('"') and atxt.endswith('"'):
                    try:
                        e.value = filt.ColumnDef.from_column(
                            self.datatab.columns[atxt[1:-1]])
                    except KeyError:
                        raise Exception("No such data column: {}".format(atxt))
                elif e.column.dt_type in ["ENUM"]:
                    e.value = ecol.from_repr(atxt)
                elif e.column.dt_type in ["BOOL"]:
                    e.value = ecol.from_repr(atxt[:-8])
                elif e.column.dt_type in ["INT"]:
                    if e.action != "one of":
                        e.value = int(atxt)
                    else:
                        e.value = list(map(int, atxt.split(',')))
                elif e.column.dt_type in ["REAL"]:
                    e.value = float(atxt)
                elif e.column.dt_type in ["TEXT"]:
                    if len(atxt) < 2 or atxt[0] != "'" or atxt[-1] != "'":
                        raise Exception("Use single quotes to set "
                                        "text parameter.")
                    e.value = atxt
            ret.entries.append(e)
        self._ret_value = ret

    def accept(self):
        try:
            self._check_input()
            self._assemble_return()
            super().accept()
        except Exception as e:
            qtcommon.message_exc(self, "Input error", e=e)

    def reject(self):
        super().reject()

    def ret_value(self):
        return self._ret_value
