#!/usr/bin/env python3
"""
2) Option representation classes (are used for OptionsList building):
    SimpleOptionEntry - QLabel (for display) + QLineEdit (for edit).
        Can be used for arbitrary str, int, float data.

    BoundedIntOptionEntry - QLabel + QSpinEdit.
        Used for integers with defined bounds

    BoolOptionEntry - QCheckBox + QCheckBox. Boolean entries.

    SingleChoiceOptionEntry - QLabel + QComboBox.
        Pick a single string from a string set

    MultipleChoiseOptionEntry - Multiple QLabels + External widget
        Pick sublist of strings from a string set

    XYOptionEntry - QLabel + pair of QLineEdits.
        Used for classes with x, y properties
"""
import copy
import os
from PyQt5 import QtCore, QtWidgets, QtGui
import resources    # noqa
try:
    from bgui import optview
except ImportError:
    import optview

_tmp = None


# option entries types
class SimpleOptionEntry(optview.OptionEntry):
    "simple str, int, float option entries "
    def __init__(self, data, member_name):
        super().__init__(data, member_name)
        self.tp = type(self.get())

    def display_widget(self):
        return self.conf._label(str(self))

    def edit_widget(self, parent):
        wdg = QtWidgets.QLineEdit(parent)
        wdg.setText(str(self))
        return wdg

    def fill_display_widget(self, wdg):
        wdg.setText(str(self))

    def set_from_widget(self, widget):
        self.set(self.tp(widget.text()))


class BoundedIntOptionEntry(SimpleOptionEntry):
    " integer value within [minv, maxv] "
    def __init__(self, data, member_name, minv=-2147483647, maxv=2147483647):
        self.minv = minv
        self.maxv = maxv
        super(BoundedIntOptionEntry, self).__init__(data, member_name)

    def _check_proc(self, v):
        return v >= self.minv and v <= self.maxv

    def edit_widget(self, parent):
        wdg = QtWidgets.QSpinBox(parent)
        wdg.setMinimum(self.minv)
        wdg.setMaximum(self.maxv)
        wdg.setValue(self.get())
        return wdg

    def set_from_widget(self, widget):
        self.set(widget.value())


class SingleChoiceOptionEntry(SimpleOptionEntry):
    "string value from combobox"
    def __init__(self, data, member_name, values):
        self.values = copy.deepcopy(values)
        super(SingleChoiceOptionEntry, self).__init__(data, member_name)

    def _check_proc(self, v):
        return v in self.values

    def edit_widget(self, parent):
        wdg = QtWidgets.QComboBox(parent)
        wdg.addItems(self.values)
        wdg.setCurrentIndex(self.values.index(self.get()))
        return wdg

    def set_from_widget(self, widget):
        self.set(widget.currentText())


class BoolOptionEntry(SimpleOptionEntry):
    " boolean flag option"
    def __init__(self, data, member_name):
        super(BoolOptionEntry, self).__init__(data, member_name)

    def _chbox_widget(self, parent=None):
        wdg = QtWidgets.QCheckBox(parent)
        wdg.setChecked(self.get())
        return wdg

    def display_widget(self):
        return self._chbox_widget()

    def fill_display_widget(self, wdg):
        wdg.setChecked(self.get())

    def edit_widget(self, parent):
        return self._chbox_widget(parent)

    def set_from_widget(self, widget):
        self.set(widget.isChecked())


class XYOptionEntry(SimpleOptionEntry):
    "x, y point option entry"
    def __init__(self, data, member_name):
        super(XYOptionEntry, self).__init__(data, member_name)
        self.__last_paint = True

    def _check_proc(self, val):
        try:
            return isinstance(val.x, float) and isinstance(val.y, float)
        except:
            return False

    def __str__(self):
        v = self.get()
        return "[" + str(v.x) + ",  " + str(v.y) + "]"

    def display_lines(self):
        return 1

    def edit_lines(self):
        return 3

    class EditWidget(QtWidgets.QWidget):
        " pair of QLineEdits with X, Y labels"
        def __init__(self, x, y, parent):
            super(XYOptionEntry.EditWidget, self).__init__(parent)
            self.xed = QtWidgets.QLineEdit(str(x))
            self.yed = QtWidgets.QLineEdit(str(y))
            self.setFocusProxy(self.xed)
            layout = QtWidgets.QGridLayout()
            layout.addWidget(QtWidgets.QLabel("X"), 0, 0)
            layout.addWidget(self.xed, 0, 1)
            layout.addWidget(QtWidgets.QLabel("Y"), 1, 0)
            layout.addWidget(self.yed, 1, 1)
            layout.setVerticalSpacing(0)
            self.setLayout(layout)
            self.setAutoFillBackground(True)

    def display_widget(self):
        self.__last_paint = True
        return super().display_widget()

    def fill_display_widget(self, w):
        self.__last_paint = True
        return super().fill_display_widget(w)

    def edit_widget(self, parent):
        self.__last_paint = False
        v = self.get()
        return XYOptionEntry.EditWidget(v.x, v.y, parent)

    def set_from_widget(self, widget):
        try:
            x = float(widget.xed.text())
            y = float(widget.yed.text())
            self.get().x = x
            self.get().y = y
        except:
            QtCore.qDebug("Invalid x, y value")


class MultipleChoiceOptionEntry(optview.OptionEntry):
    'Unique sublist from a list of string. Ordering matters.'

    def __init__(self, data, member_name, values):
        self.values = copy.deepcopy(values)
        super(MultipleChoiceOptionEntry, self).__init__(data, member_name)

    def _check_proc(self, val):
        return all(v in self.values for v in val)

    def display_widget(self):
        " generates display widget with data "
        wdg = QtWidgets.QFrame()
        lab = QtWidgets.QVBoxLayout()
        wdg.setLayout(lab)
        self.fill_display_widget(wdg)
        return wdg

    def _clear_layout(self, wdg):
        def deleteItems(layout):  # noqa
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()
                    else:
                        deleteItems(item.layout())
        deleteItems(wdg.layout())

    def fill_display_widget(self, wdg):
        self._clear_layout(wdg)
        lab = wdg.layout()
        lab.addStretch(1)
        for v in self.get():
            lab.addWidget(self.conf._label(v))
        lab.setSpacing(self.conf.vert_gap)
        lab.setContentsMargins(0, 0, 0, 0)
        lab.addStretch(1)

    def display_lines(self):
        return len(self.get())

    class EditWidget(QtWidgets.QWidget):
        'widget for creating unique sublist'
        def __init__(self, data, parent):
            # ---- building window
            super(MultipleChoiceOptionEntry.EditWidget, self).__init__(parent)
            self.lw1 = QtWidgets.QListWidget()
            self.lw2 = QtWidgets.QListWidget()
            btleft = QtWidgets.QPushButton()
            btleft.setText("<--")
            btleft.clicked.connect(self.left_click)
            btleft.setFocusPolicy(QtCore.Qt.NoFocus)
            btright = QtWidgets.QPushButton()
            btright.clicked.connect(self.right_click)
            btright.setText("-->")
            btright.setFocusPolicy(QtCore.Qt.NoFocus)
            bbox = QtWidgets.QDialogButtonBox()
            bbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel |
                                    QtWidgets.QDialogButtonBox.Ok)
            bbox.accepted.connect(self.ok_action)
            bbox.rejected.connect(self.cancel_action)
            # left/right buttons
            button_frame = QtWidgets.QFrame()
            button_frame.setLayout(QtWidgets.QVBoxLayout())
            button_frame.layout().addStretch(1.0)
            button_frame.layout().addWidget(btleft)
            button_frame.layout().addWidget(btright)
            button_frame.layout().addStretch(1.0)
            # widget
            widget_frame = QtWidgets.QFrame()
            widget_frame.setLayout(QtWidgets.QHBoxLayout())
            widget_frame.layout().addWidget(self.lw1)
            widget_frame.layout().addWidget(button_frame)
            widget_frame.layout().addWidget(self.lw2)
            # window
            self.setFocusProxy(self.lw1)
            self.setLayout(QtWidgets.QVBoxLayout())
            self.layout().addWidget(widget_frame)
            self.layout().addWidget(bbox)
            self.resize(400, 300)
            self.setWindowModality(QtCore.Qt.WindowModal)
            # ---- data
            self.data = data
            self.left_column = data.get()
            self.right_column = list(filter(
                lambda x: x not in self.left_column, data.values))
            self._fill()

        def _fill_column(self, lw, col, s):
            lw.clear()
            lw.addItems(col)
            if len(col) > 0:
                s = min(s, len(col) - 1)
                lw.setCurrentRow(s)

        def _fill(self, s1=0, s2=0):
            """fill widget lists from data arrays
                s1, s2 - selected row indicies
            """
            self._fill_column(self.lw1, self.left_column, s1)
            self._fill_column(self.lw2, self.right_column, s2)

        def _add_rem(self, remcol, addcol, itms):
            s1, s2 = self.lw1.currentRow(), self.lw2.currentRow()
            for it in [str(v.text()) for v in itms]:
                remcol.remove(it)
                addcol.append(it)
            self._fill(s1, s2)

        def left_click(self):
            self._add_rem(self.right_column, self.left_column,
                          self.lw2.selectedItems())

        def right_click(self):
            self._add_rem(self.left_column, self.right_column,
                          self.lw1.selectedItems())

        def ok_action(self):
            self.data.set(self.left_column)
            self.close()

        def cancel_action(self):
            self.close()

        def keyPressEvent(self, event):   # noqa
            k = event.key()
            if self.focusWidget() is self.lw1 and k == QtCore.Qt.Key_Right:
                return self.right_click()
            elif self.focusWidget() is self.lw2 and k == QtCore.Qt.Key_Left:
                return self.left_click()
            elif k in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
                return self.ok_action()
            super(self.__class__, self).keyPressEvent(event)

    def edit_widget(self, parent=None):
        # create widget in a separate window without parents
        return MultipleChoiceOptionEntry.EditWidget(self, None)

    def get(self):
        v = super().get()
        return copy.deepcopy(v)

    def set(self, val):
        v = copy.deepcopy(val)
        super(MultipleChoiceOptionEntry, self).set(v)

    def set_from_widget(self, editor):
        # value was set in editor widget ok action
        pass

    def __str__(self):
        return "; ".join(self.get())


class CheckTreeOptionEntry(optview.OptionEntry):
    MaximumPossibleLength = 10

    def __init__(self, data, member_name, expansion_level=1):
        self.values = copy.deepcopy(data.odata().__dict__[member_name])
        super().__init__(data, member_name)
        self.__ignore_cs = False
        self.__expansion = self._expansion_from_level(expansion_level)
        self.maxlen = min(self.MaximumPossibleLength, self._lines_count(False))

    def _expansion_from_level(self, lv):
        ret = []  # expanded addreses

        def analyze_children(dct, addr, curlv):
            for i, (k, v) in enumerate(dct.items()):
                addr.append(i)
                if isinstance(v, dict):
                    if curlv < lv:
                        ret.append(addr[:])
                    analyze_children(v, addr, curlv+1)
                addr.pop()
        a = []
        analyze_children(self.values, a, 0)
        return ret

    def _expansion_from_widget(self, wdg):
        ret = []  # expanded addreses

        def analyze_children(item, addr):
            for i in range(item.childCount()):
                addr.append(i)
                ch = item.child(i)
                if ch.childCount() > 0:
                    if ch.isExpanded():
                        ret.append(addr[:])
                    analyze_children(ch, addr)
                addr.pop()
        a = []
        analyze_children(wdg.invisibleRootItem(), a)
        return ret

    def _expansion_to_widget(self, wdg):
        # hide all
        it = QtWidgets.QTreeWidgetItemIterator(
                wdg, QtWidgets.QTreeWidgetItemIterator.HasChildren)
        while it.value():
            it.value().setExpanded(False)
            it += 1

        # open only needed
        def item_by_address(addr):
            ret = wdg.invisibleRootItem()
            for a in addr:
                ret = ret.child(a)
            return ret
        for e in self.__expansion:
            item_by_address(e).setExpanded(True)

    def _lines_count(self, only_visible):
        h = [';'.join(map(str, x)) for x in self.__expansion]

        def analyze_children(dct, a):
            r = len(dct)
            for i, (k, v) in enumerate(dct.items()):
                a.append(i)
                deep = True
                if only_visible:
                    h2 = ';'.join(map(str, a))
                    if h2 not in h:
                        deep = False
                if deep and isinstance(v, dict):
                    r += analyze_children(v, a)
                a.pop()
            return r

        a = []
        ret = analyze_children(self.values, a)
        return ret

    def _fill_item(self, item, value):
        item.setExpanded(True)
        for key, val in value.items():
            child = QtWidgets.QTreeWidgetItem()
            child.setText(0, str(key))
            item.addChild(child)
            if isinstance(val, bool):
                # here we disable signals and invoke handler manually,
                # otherwise it doesnt work properly
                self.__ignore_cs = True
                child.setCheckState(
                    0, QtCore.Qt.Checked if val else QtCore.Qt.Unchecked)
                self.__ignore_cs = False
                self._checks_handler(child, 0)
            else:
                self._fill_item(child, val)

    def _checks_handler(self, item, column):
        if self.__ignore_cs:
            return
        self.__ignore_cs = True
        self._set_parent_checks(item)
        self._set_children_checks(item)
        self.__ignore_cs = False

    def _set_parent_checks(self, item):
        par = item.parent()
        if par is None:
            return
        chs = item.checkState(0)
        for i in range(par.childCount()):
            if par.child(i).checkState(0) != chs:
                chs = QtCore.Qt.PartiallyChecked
                break
        par.setCheckState(0, chs)
        self._set_parent_checks(par)

    def _set_children_checks(self, item):
        chs = item.checkState(0)
        for i in range(item.childCount()):
            c = item.child(i)
            c.setCheckState(0, chs)
            self._set_children_checks(c)

    def _set_from_addr(self, addr, val):
        obj = self.values
        for a in addr[:-1]:
            k = list(obj.keys())
            obj = obj[k[a]]
        obj[list(obj.keys())[addr[-1]]] = val

    def _create_widget(self, parent=None):
        wdg = QtWidgets.QTreeWidget(parent)
        wdg.itemChanged.connect(self._checks_handler)
        wdg.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        wdg.setHeaderHidden(True)
        wdg.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.fill_display_widget(wdg)
        return wdg

    def display_widget(self, parent=None):
        ret = self._create_widget(parent)
        qp = QtGui.QPalette(ret.palette())
        qp.setColor(QtGui.QPalette.Base, QtGui.QColor(0, 0, 0, 0))
        ret.setPalette(qp)
        return ret

    def edit_widget(self, parent=None):
        ret = self._create_widget(parent)
        return ret

    def fill_display_widget(self, wdg):
        wdg.clear()
        self._fill_item(wdg.invisibleRootItem(), self.values)
        self._expansion_to_widget(wdg)

    def display_lines(self):
        return 1.7*self._lines_count(True)

    def edit_lines(self):
        return 1.7*self.maxlen

    def set_from_widget(self, editor):
        def _set_from_item(parent, cindex, addr):
            addr.append(cindex)
            itm = parent.child(cindex)
            if itm.childCount() == 0:
                self._set_from_addr(
                    addr, itm.checkState(0) == QtCore.Qt.Checked)
            else:
                for i in range(itm.childCount()):
                    _set_from_item(itm, i, addr)
                    addr.pop()

        itm = editor.invisibleRootItem()
        for i in range(itm.childCount()):
            addr = []
            _set_from_item(itm, i, addr)
        self.__expansion = self._expansion_from_widget(editor)
        self.set(self.values)

    def __str__(self):
        return str(self.values)


class LineEditWithButton(QtWidgets.QLineEdit):
    def __init__(self, txt, parent):
        super().__init__(parent)
        self.setText(txt)
        self.button = self.addAction(QtGui.QIcon(':/more16'),
                                     QtWidgets.QLineEdit.TrailingPosition)


class SaveFileOptionEntry(SimpleOptionEntry):
    def __init__(self, data, member_name, filter_list):
        """ filter list: [(name, (list of extensions without *)),] except *.*
        """
        super().__init__(data, member_name)
        self.filter_list = filter_list
        self._filters = []
        for a in filter_list:
            sd1 = ", ".join(a[1])
            sd2 = " ".join(["*." + x for x in a[1]])
            self._filters.append("{0} ({1})({2})".format(a[0], sd1, sd2))
        self._filters.append("All Files(*)")

    def filter_line(self):
        # place needed filter to start position so
        # it doesn't disturb filename
        i = self.get_filter()
        fff = self._filters[:]
        fff.remove(self._filters[i])
        fff.insert(0, self._filters[i])
        return fff

    def get_filter(self):
        fn, ext = os.path.splitext(self.get())
        if not fn:
            return 0
        for i, a in enumerate(self.filter_list):
            if ext[1:] in a[1]:
                return i
        return -1

    def show_dialog(self, parent=None):
        fl = self.filter_line()
        fn = QtWidgets.QFileDialog.getSaveFileName(
            parent, "Save file", self.get(), ';;'.join(fl), fl[0],
            QtWidgets.QFileDialog.DontConfirmOverwrite)
        if fn[0]:
            self.set(fn[0])

    def edit_widget(self, parent):
        w = LineEditWithButton(self.get(), parent)
        w.button.triggered.connect(lambda: self.show_dialog(parent))
        return w

# =================== Usage example
if __name__ == "__main__":
    import sys
    from collections import OrderedDict

    class Point(object):
        def __init__(self, x, y):
            self.x, self.y = x, y

    class CircOptionsSet:
        def __init__(self):
            self.name = "CircularGrid1"
            self.px = 0.0
            self.py = 0.0
            self.rad = 1.0
            self.Nr = 10
            self.Na = 10
            self.is_trian = True
            self.units = "units"
            self.grids = ["Grid1", "Grid2", "Grid3"]
            self.point = Point(3.4, 6.7)
            self.multikeys = OrderedDict([
                ("ALL", OrderedDict([
                    ("as", True),
                    ("bs", False),
                    ("cs", False),
                    ("AndAgain", OrderedDict([
                        ("aa", False),
                        ("dd", False)
                    ]))
                ])),
                ("Other", False),
                ("Another", True),
            ])

    class OContainer(optview.OptionsHolderInterface):
        def __init__(self):
            self.cos = CircOptionsSet()
            self.checks = object()

        def odata(self):
            return self.cos

        def odata_status(self):
            return self.checks

    def optionlist_for_circ(opt):
        # all possible values for opt.units, opt.grids
        a_units = ["units", "%"]
        a_grids = ["Grid1", "Grid2", "Grid3", "Grid4", "Grid5"]
        # build an input array for OptionsList:
        #   [(Caption, OptionName, OptionEntry), ....]
        ar = [
                ("Basic", "Grid name", SimpleOptionEntry(opt, "name")),
                ("Geometry", "X coordinate", SimpleOptionEntry(opt, "px")),
                ("Geometry", "Y coordinate", SimpleOptionEntry(opt, "py")),
                ("Geometry", "Radius", SimpleOptionEntry(opt, "rad")),
                ("Partition", "Radius Partition",
                    BoundedIntOptionEntry(opt, "Nr", 1, 1e2)),
                ("Partition", "Arch Partition",
                    BoundedIntOptionEntry(opt, "Na", 3, 1e2)),
                ("Partition", "Triangulate center cell",
                    BoolOptionEntry(opt, "is_trian")),
                ("Additional", "Units",
                    SingleChoiceOptionEntry(opt, "units", a_units)),
                ("Additional", "Choice",
                    MultipleChoiceOptionEntry(opt, "grids", a_grids)),
                ("Additional", "Point", XYOptionEntry(opt, "point")),
                ("Additional", "Tree",
                    CheckTreeOptionEntry(opt, "multikeys"))
            ]
        return optview.OptionsList(ar)

    class Window(QtWidgets.QDialog):
        def __init__(self, opt, parent=None):
            super(Window, self).__init__(parent)
            self.resize(400, 500)
            self.button = QtWidgets.QPushButton()
            self.button.setText("Options to stdout")
            # !Option widget
            self.opt_list = optionlist_for_circ(opt)
            self.tab = optview.OptionsView(self.opt_list, parent=self)

            # add smart active row management
            def is_active(entry):
                # matches name entry activity with is_trian flag
                if entry.member_name == "name":
                    return entry.data.is_trian
                else:
                    return True
            self.tab.is_active_delegate(is_active)

            # window and layout
            vert_layout = QtWidgets.QVBoxLayout()
            vert_layout.addWidget(self.tab)
            vert_layout.addWidget(self.button)

            self.setLayout(vert_layout)

            self.button.clicked.connect(self.buttonClicked)

        def buttonClicked(self):   # noqa
            print(self.opt_list)

    app = QtWidgets.QApplication(sys.argv)
    win = Window(OContainer())
    win.show()
    sys.exit(app.exec_())
