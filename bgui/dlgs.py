#!/usr/bin/env python3
import sys
import copy
import collections
from PyQt5 import QtCore, QtWidgets
from bgui import optview, optwdg


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

    def set_odata_entry(self, code, value):
        " set odata.code = value with the respective callback"
        self.odata().__dict__[code] = value
        self.on_value_change(code)

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
        self._odata_init()
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
        self.resize(self._sz_x, self._sz_y)

    def resizeEvent(self, e):   # noqa
        self.__class__._sz_x = e.size().width()
        self.__class__._sz_y = e.size().height()
        super().resizeEvent(e)

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

    def _odata_init(self):
        "called before olist call. It modifies odata() global  entries"
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

    def on_value_change(self, code):
        "fired after odata().code is changed"
        pass


class GroupRowsDlg(SimpleAbstractDialog):
    _sz_x, _sz_y = 300, 400

    def __init__(self, lst_categories, parent=None):
        self.cats = lst_categories
        super().__init__(parent)
        self.setWindowTitle("Group Rows")

    def _odata_init(self):
        e = collections.OrderedDict([(
            "All categories", collections.OrderedDict())])
        for c in self.cats:
            e["All categories"][c] = True
        self.set_odata_entry("cat", e)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.algo = 'arithmetic mean'

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
        for k, v in od.cat['All categories'].items():
            if v:
                ret.append(k)
        return [od.algo, ret]


class CollapseColumnsDlg(SimpleAbstractDialog):
    _sz_x, _sz_y = 400, 300

    def __init__(self, lst_categories, parent=None):
        self.cats = lst_categories
        super().__init__(parent)
        self.odata().cats = lst_categories
        self.setWindowTitle("Collapse columns")

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.delim = '/'
        obj.do_hide = True

    def _odata_init(self):
        e = collections.OrderedDict([(
            "All categories", collections.OrderedDict())])
        for c in self.cats:
            e["All categories"][c] = False
        self.set_odata_entry("cat", e)

    def olist(self):
        return optview.OptionsList([
            ("Basic", "Hide used columns", optwdg.BoolOptionEntry(
                self, "do_hide")),
            ("Basic", "Delimiter", optwdg.SimpleOptionEntry(
                self, "delim")),
            ("Categories", "Column list", optwdg.CheckTreeOptionEntry(
                self, "cat", 1)),
            ])

    def ret_value(self):
        "-> categories list"
        od = self.odata()
        ret = [k for k, v in od.cat['All categories'].items() if v]
        return [od.do_hide, od.delim, ret]


class FilterRowsDlg(SimpleAbstractDialog):
    _sz_x, _sz_y = 350, 400

    def __init__(self, data, parent):
        " data - dt.dattab object "
        self.data = data
        super().__init__(parent)
        self.setWindowTitle("Filter Rows")

    def _default_odata(self, obj):
        obj.algo = "Remove"
        obj.operation = "AND"
        obj.bv_group = False
        obj.redstatus = "Any column"
        obj.emptycell = "Any column"

    def _default_odata_status(self, obj):
        obj.redstatus = False
        obj.emptycell = False

    def _odata_init(self):
        for k in self.odata().__dict__:
            if k[:3] == "cat":
                self.odata().__dict__.pop(k)
        for k in self.odata_status().__dict__:
            if k[:3] == "cat":
                self.odata_status().__dict__.pop(k)

        for i, cat in enumerate(self.data.get_categories()):
            nm = "cat" + str(i)
            if cat.dt_type == "ENUM":
                self.set_odata_entry(
                    nm, next(iter(cat.possible_values_short.values())))
            elif cat.dt_type == "INTEGER":
                self.set_odata_entry(nm, 1)
            elif cat.dt_type == "BOOLEAN":
                self.set_odata_entry(nm, False)

        for i, cat in enumerate(self.data.get_categories()):
            nm = "cat" + str(i)
            self.odata_status().__dict__[nm] = False

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


class ExportTablesDlg(SimpleAbstractDialog):
    _sz_x, _sz_y = 400, 300

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export table")

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.filename = ''
        obj.with_caption = True
        obj.with_id = True
        obj.format = "plain text"
        obj.numeric_enums = False
        obj.grouped_categories = 'None'

    def olist(self):
        flt = [('Excel files', ('xlsx',))]
        return optview.OptionsList([
            ("Export to", "Filename", optwdg.SaveFileOptionEntry(
                self, "filename", flt)),
            ("Export to", "Format", optwdg.SingleChoiceOptionEntry(
                self, "format", ["xlsx", "plain text"])),
            ("Additional", "Include caption", optwdg.BoolOptionEntry(
                self, "with_caption")),
            ("Additional", "Include id column", optwdg.BoolOptionEntry(
                self, "with_id")),
            ("Additional", "Enums as integers", optwdg.BoolOptionEntry(
                self, "numeric_enums")),
            ("Additional", "Non-unique groups", optwdg.SingleChoiceOptionEntry(
                self, "grouped_categories", ['None', 'Comma separated',
                                             'Unique count'])),
            ])

    def on_value_change(self, code):
        if code == 'filename':
            if self.odata().filename[-5:] == '.xlsx':
                self.set_odata_entry('format', 'xlsx')
            elif self.odata().filename[-4:] == '.txt':
                self.set_odata_entry('format', 'plain text')

    def accept(self):
        import pathlib
        fn = self.odata().filename
        if pathlib.Path(fn).is_file():
            reply = QtWidgets.QMessageBox.question(
                self, "Overwrite file?",
                'The file "{}" already exists.\n'
                'Do you want to overwrite it?'.format(fn),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if reply != QtWidgets.QMessageBox.Yes:
                return
        super().accept()

    def ret_value(self):
        return copy.deepcopy(self.odata())

    def check_input(self):
        if not self.odata().filename:
            raise Exception("Invalid filename")


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
