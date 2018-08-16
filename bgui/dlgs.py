#!/usr/bin/env python3
import sys
import math
import copy
import collections
from PyQt5 import QtCore, QtWidgets
from bgui import optview, optwdg


class Point2(object):
    ' point in (x,y) plane '
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return str(self.x) + " " + str(self.y)

    def dist(self, p1):
        " -> distance between self and p1 "
        x, y = p1.x - self.x, p1.y - self.y
        return math.sqrt(x * x + y * y)

    def dist0(self):
        " -> distance between self and (0, 0) "
        x, y = self.x, self.y
        return math.sqrt(x * x + y * y)

    @classmethod
    def fromstring(cls, s):
        s2 = s.split()
        return cls(float(s2[0]), float(s2[1]))


class _BackGroundWorkerCB(QtCore.QThread):
    """ Background procedure with callback caller
        for call from ProgressProcedureDlg
    """
    def __init__(self, emitter, func, args):
        """ emitter - pyqtSignal that emits signal,
            func(*args, callback_fun) - target procedure,
            callback function should be declared as
                int callback_fun(QString BaseName, QString SubName,
                    double proc1, double proc2)
            it should return 1 for cancellation requiry and 0 otherwise

        """
        super(_BackGroundWorkerCB, self).__init__()
        self.emitter = emitter
        self.func = func
        self.args = args + (self._get_callback(),)
        self.proceed, self._result = True, None

    def run(self):
        self.proceed = True
        self._result = self.func(*self.args)

    def _emit(self, n1, n2, p1, p2):
        self.emitter.emit(n1, n2, p1, p2)

    def _get_callback(self):
        import ctypes as ct

        def cb(n1, n2, p1, p2):
            self._emit(n1, n2, p1, p2)
            return 0 if self.proceed else 1

        # if target function is a c function then convert callback to
        # a c function pointer
        if isinstance(self.func, ct._CFuncPtr):
            cbfunc = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_char_p,
                                  ct.c_double, ct.c_double)
            cb2 = cbfunc(cb)
            return cb2
        else:
            return cb


class ProgressProcedureDlg(QtWidgets.QDialog):
    """ ProgressBar/Cancel dialog window which wraps time consuming
        procedure calls.
    """

    emitter = QtCore.pyqtSignal('QString', 'QString', 'double', 'double')

    def __init__(self, func, args, parent=None):
        """ func(*args, callback_fun) - target procedure,
            callback_fun should be declared as
                int callback_fun(QString BaseName, QString SubName,
                    double proc1, double proc2)
            it should return 1 for cancellation requiry and 0 otherwise
        """
        flags = QtCore.Qt.Dialog \
            | QtCore.Qt.CustomizeWindowHint \
            | QtCore.Qt.WindowTitleHint
        super().__init__(parent, flags)

        # design
        self._label1 = QtWidgets.QLabel()
        self._label2 = QtWidgets.QLabel()
        self._progbar1 = QtWidgets.QProgressBar()
        self._progbar2 = QtWidgets.QProgressBar()
        self._buttonbox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel)
        self._buttonbox.setCenterButtons(True)
        self._buttonbox.rejected.connect(self._cancel_pressed)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._label1)
        layout.addWidget(self._progbar1)
        layout.addWidget(self._label2)
        layout.addWidget(self._progbar2)
        layout.addWidget(self._buttonbox)
        self.setLayout(layout)
        self.setFixedSize(400, 150)
        self.setModal(True)

        # worker
        self.emitter.connect(self._fill)

        self._worker = _BackGroundWorkerCB(self.emitter, func, args)
        self._worker.finished.connect(self._fin)

    def exec_(self):
        self.show()  # show first to avoid delay
        self._worker.start()
        return super(ProgressProcedureDlg, self).exec_()

    def _fill(self, n1, n2, p1, p2):
        self.setWindowTitle(n1)
        self._label1.setText(n1)
        self._label2.setText(n2)
        self._progbar1.setValue(100 * p1)
        self._progbar2.setValue(100 * p2)

    def _cancel_pressed(self):
        self._worker.proceed = False
        self._worker.terminate()

    def _fin(self):
        self._result = self._worker._result
        self.close()

    def get_result(self):
        return self._result


class SimpleAbstractDialog(QtWidgets.QDialog, optview.OptionsHolderInterface):
    "Abstract dialog for option set"
    class _OData(object):
        pass

    def odata(self):
        """returns options struct child class singleton which stores
        last dialog execution"""
        if not hasattr(self, "_odata"):
            setattr(self.__class__, "_odata", SimpleAbstractDialog._OData())
            self._default_odata(self._odata)
        return self._odata

    def odata_status(self):
        """returns options struct child class singleton which stores
        last dialog execution"""
        if not hasattr(self, "_odata_status"):
            setattr(self.__class__, "_odata_status",
                    SimpleAbstractDialog._OData())
            self._default_odata_status(self._odata_status)
        return self._odata_status

    def __init__(self, parent=None):
        super(SimpleAbstractDialog, self).__init__(parent)
        oview = optview.OptionsView(self.olist())
        oview.is_active_delegate(self._active_entries)
        buttonbox = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok |
                QtWidgets.QDialogButtonBox.Cancel)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(oview)
        layout.addWidget(buttonbox)

    def accept(self):
        "check errors and invoke parent accept"
        try:
            self.check_input()
            super(SimpleAbstractDialog, self).accept()
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                    self, "Warning", "Invalid Input: %s" % str(e))

    # functions for overriding
    def _default_odata(self, obj):
        "fills options struct obj with default values"
        raise NotImplementedError

    def _default_odata_status(self, obj):
        "fills options struct obj with default values"
        pass

    def olist(self):
        "-> optview.OptionsList"
        raise NotImplementedError

    def ret_value(self):
        "-> dict from option struct"
        raise NotImplementedError

    def check_input(self):
        "throws Exception if self.odata() has invalid fields"
        pass

    def _active_entries(self, entry):
        "return False for non-active entries"
        return True


class GroupRowsDlg(SimpleAbstractDialog):

    def __init__(self, lst_categories, parent=None):
        self.cats = lst_categories
        super().__init__(parent)
        self.odata().cats = lst_categories
        self.resize(300, 400)
        self.setWindowTitle("Group Rows")

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.algo = 'arithmetic mean'
        obj.cat = collections.OrderedDict([(
            "All", collections.OrderedDict())])
        for c in self.cats:
            obj.cat["All"][c] = True

    def olist(self):
        return optview.OptionsList([
            ("Merging", "Algorithm", optwdg.SingleChoiceOptionEntry(
                self, "algo", ['arithmetic mean', 'median',
                               'maximum', 'minimum', 'median+', 'median-'])),
            ("Categories", "Group by", optwdg.CheckTreeOptionEntry(
                self, "cat", 1)),
            ])

    def ret_value(self):
        "-> categories list"
        od = copy.deepcopy(self.odata())
        if od.algo == 'arithmetic mean':
            od.algo = 'amean'
        elif od.algo == 'maximum':
            od.algo = 'max'
        elif od.algo == 'minimum':
            od.algo = 'min'
        ret = []
        for k, v in od.cat['All'].items():
            if v:
                ret.append(k)
        return [od.algo, ret]


class FilterRowsDlg(SimpleAbstractDialog):

    def __init__(self, data, parent):
        " data - dt.dattab object "
        self.data = data
        super().__init__(parent)
        self.resize(350, 400)
        self.setWindowTitle("Filter Rows")

    def _default_odata(self, obj):
        obj.algo = "Remove"
        obj.operation = "AND"
        obj.bv_group = False
        obj.redstatus = "Any column"
        obj.emptycell = "Any column"
        for i, cat in enumerate(self.data.get_categories()):
            nm = "cat" + str(i)
            if cat.dt_type == "ENUM":
                obj.__dict__[nm] = next(iter(
                    cat.possible_values_short.values()))
            elif cat.dt_type == "INTEGER":
                obj.__dict__[nm] = 1
            elif cat.dt_type == "BOOLEAN":
                obj.__dict__[nm] = False

    def _default_odata_status(self, obj):
        obj.redstatus = False
        obj.emptycell = False
        for i, cat in enumerate(self.data.get_categories()):
            nm = "cat" + str(i)
            obj.__dict__[nm] = False

    def olist(self):
        oe_ch = optwdg.SingleChoiceOptionEntry
        # Exclusion algorithm
        op = [("Exclusion", "Algorithm", oe_ch(
                self, "algo", ["Remove", "Leave only"])),
              ("Exclusion", "Operation", oe_ch(
                self, "operation", ["AND", "OR"]))]
        # Categories
        for i, cat in enumerate(self.data.get_categories()):
            fnm = cat.name
            nm = "cat" + str(i)
            if cat.dt_type == "ENUM":
                pv = cat.possible_values_short.values()
                op.append(("Category", fnm, oe_ch(self, nm, list(pv))))
            elif cat.dt_type == "INTEGER":
                op.append(("Category", fnm, optwdg.BoundedIntOptionEntry(
                        self, nm)))
            elif cat.dt_type == "BOOLEAN":
                op.append(("Category", fnm, optwdg.BoolOptionEntry(
                    self, nm)))
        # Other
        op.append(("Bad Values", "Whole group", optwdg.BoolOptionEntry(
                self, "bv_group")))
        clist = ["Any column", "Any data column"]
        op.append(("Bad Values", "Red Status", oe_ch(
                self, "redstatus", clist)))
        op.append(("Bad Values", "Empty Cells", oe_ch(
                self, "emptycell", clist)))

        return optview.OptionsList(op)

    def ret_value(self):
        """ -> Filters list """
        from bdata import dtab
        ret = []
        od = self.odata()
        # categories
        ret_nm, ret_val = [], []
        for i, cat in enumerate(self.data.get_categories()):
            nm = "cat" + str(i)
            vl = od.__dict__[nm]
            if self.odata_status().__dict__[nm]:
                ret_nm.append(cat.name)
                vl = cat.from_repr(vl)
                ret_val.append(vl)
        if len(ret_nm) == 0:
            ret = []
        else:
            rem = od.algo == "Remove"
            use_and = od.operation == 'AND'
            ret = [dtab.FilterByValue(ret_nm, ret_val, rem, use_and)]

        # red status, Empty Cells
        # TODO

        return ret


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    # d = AddUnfRectGrid()
    # d.exec_()
    # s = ";".join(map(str, d.ret_value()))
    # print(s)

    # def tcfun(n, cb):
    #     for i in range(n):
    #         cb("proc1", "proc2", float(i)/n, 0.33)
    #         time.sleep(0.1)
    #     return 2*n

    # e = ProgressProcedureDlg(tcfun, (30,), None)
    # e.exec_()
    # print(e.get_result())
    # e.exec_()
    # print(e.get_result())

    # d = GroupLinesDlg(["AG", "BA", "CA"])
    # d.exec_();
    # print(d.ret_value())
