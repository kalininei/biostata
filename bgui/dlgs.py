#!/usr/bin/env python3
import copy
import collections
from PyQt5 import QtCore, QtWidgets
from bgui import optview, optwdg, coloring, qtcommon
from bdata import filt
from bdata import derived_tabs
from bdata import bcol


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


class OkCancelDialog(QtWidgets.QDialog):
    def __init__(self, title, parent, layout_type="vertical"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.buttonbox = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok |
                QtWidgets.QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.mainframe = QtWidgets.QFrame(self)
        if layout_type == "vertical":
            self.mainframe.setLayout(QtWidgets.QVBoxLayout())
        elif layout_type == "horizontal":
            self.mainframe.setLayout(QtWidgets.QHBoxLayout())
        elif layout_type == "grid":
            self.mainframe.setLayout(QtWidgets.QGridLayout())
        else:
            raise Exception("Unknown layout {}".format(layout_type))
        self.mainframe.layout().setContentsMargins(0, 0, 0, 0)

        self.layout().addWidget(self.mainframe)
        self.layout().addWidget(self.buttonbox)


class SimpleAbstractDialog(optview.OptionsHolderInterface, OkCancelDialog):
    def __init__(self, title, parent=None):
        OkCancelDialog.__init__(self, title, parent)
        optview.OptionsHolderInterface.__init__(self)
        self.mainframe.layout().addWidget(self.oview)

    def accept(self):
        "check errors and invoke parent accept"
        if self.confirm_input():
            QtWidgets.QDialog.accept(self)


@qtcommon.hold_position
class GroupRowsDlg(SimpleAbstractDialog):
    def __init__(self, lst_categories, parent=None):
        self.cats = lst_categories
        super().__init__("Group Rows", parent)
        self.resize(300, 400)

    def _odata_init(self):
        e = collections.OrderedDict([(
            "All categories", collections.OrderedDict())])
        for c in self.cats:
            e["All categories"][c] = False
        self.set_odata_entry("cat", e)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.algo = 'arithmetic mean'
        obj.cat = None

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


@qtcommon.hold_position
class CollapseColumnsDlg(SimpleAbstractDialog):
    def __init__(self, lst_categories, parent=None):
        self.cats = lst_categories
        super().__init__("Collapse columns", parent)
        self.resize(400, 300)
        self.odata().cats = lst_categories

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.delim = '-'
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


@qtcommon.hold_position
class ExportTablesDlg(SimpleAbstractDialog):
    def __init__(self, parent=None):
        super().__init__("Export table", parent)
        self.resize(400, 300)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.filename = ''
        obj.with_caption = True
        obj.with_id = True
        obj.format = "plain text"
        obj.numeric_enums = False
        obj.grouped_categories = 'None'
        obj.with_formatting = True

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
            ("Additional", "Preserve formatting", optwdg.BoolOptionEntry(
                self, "with_formatting")),
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

    def _active_entries(self, entry):
        if self.odata().format == "plain text":
            if entry.member_name == "with_formatting":
                return False
        return True

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


@qtcommon.hold_position
class RowColoringDlg(SimpleAbstractDialog):
    def __init__(self, clist, parent=None):
        # column list
        self.clist = clist
        # color schemes
        self.schemes = coloring.ColorScheme.cs_list()
        for k, v in self.schemes.items():
            self.schemes[k] = v()
        # pics will be set in _sync_schemes procedure
        self.pics = [None] * len(self.schemes)
        # none colors
        self.defcolors = collections.OrderedDict([
            ("black", (0, 0, 0)), ("white", (255, 255, 255)),
            ("red", (255, 0, 0)), ("magenta", (255, 0, 255)),
            ("yellow", (255, 255, 0)), ("aqua", (0, 255, 255))])
        # init
        super().__init__("Coloring", parent)
        self.resize(400, 300)
        self._sync_schemes()

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.column = "id"
        obj.range = "Global"
        obj.discrete = False
        obj.reversed = False
        obj.discrete_count = -1
        obj.preset = next(iter(self.schemes.keys()))
        obj.none_color = "black"

    def _odata_init(self):
        if self.odata().column not in self.clist:
            self.set_odata_entry("column", self.clist[0])

    def olist(self):
        cshnames = list(self.schemes.keys())
        return optview.OptionsList([
            ("Source", "Column", optwdg.SingleChoiceOptionEntry(
                self, "column", self.clist)),
            ("Source", "Range", optwdg.SingleChoiceOptionEntry(
                self, "range", ["Local", "Global"])),
            ("Color scheme", "Preset", optwdg.SingleChoiceWImgOptionEntry(
                self, "preset", cshnames, self.pics)),
            ("Color scheme", "None color", optwdg.SingleChoiceColorOptionEntry(
                self, "none_color",
                list(self.defcolors.keys()), list(self.defcolors.values()))),
            ("Color scheme", "Reversed", optwdg.BoolOptionEntry(
                self, "reversed")),
            ("Color scheme", "Discrete", optwdg.BoolOptionEntry(
                self, "discrete")),
            ("Color scheme", "Discrete count", optwdg.BoundedIntOptionEntry(
                self, "discrete_count", minv=-1)),
            ])

    def on_value_change(self, code):
        if code in ['discrete', 'reversed', 'discrete_count', "none_color"]:
            self._sync_schemes()

    def _active_entries(self, entry):
        if entry.member_name == 'discrete_count':
            if not self.odata().discrete:
                return False
        return True

    def ret_value(self):
        "-> column name, ColorScheme Entry, is_local_range"
        cs = self.schemes[self.odata().preset]
        is_local = self.odata().range == "Local"
        return (self.odata().column, copy.deepcopy(cs), is_local)

    def _sync_schemes(self):
        for i, v in enumerate(self.schemes.values()):
            v.set_discrete(self.odata().discrete, self.odata().discrete_count)
            v.set_reversed(self.odata().reversed)
            sw = 100
            sh = optwdg.SingleChoiceWImgOptionEntry.max_pic_height
            self.pics[i] = v.pic(sh, sw, True)
            v.set_default_color(self.defcolors[self.odata().none_color])


@qtcommon.hold_position
class NewBoolColumn(SimpleAbstractDialog):
    def __init__(self, dt, parent=None):
        # data
        self.dt = dt
        super().__init__("New boolean column", parent)
        self.resize(400, 300)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.colname = ""
        obj.colshortname = ""
        obj.type = "currently visible"
        obj.used_filters = collections.OrderedDict()
        obj.reverted = False
        obj.false_name = "No"
        obj.true_name = "Yes"

    def _odata_init(self):
        e = collections.OrderedDict()
        for f in self.dt.applicable_named_filters():
            e[f.name] = False
        self.set_odata_entry("used_filters", e)
        i = 1
        while True:
            try:
                self.dt.is_valid_column_name("bool" + str(i))
            except:
                i += 1
                continue
            self.set_odata_entry("colname", "bool" + str(i))
            self.set_odata_entry("colshortname", "b" + str(i))
            break

    def olist(self):
        return optview.OptionsList([
            ("Name", "Column name", optwdg.SimpleOptionEntry(
                self, 'colname', dostrip=True)),
            ("Name", "Short name", optwdg.SimpleOptionEntry(
                self, "colshortname", dostrip=True)),
            ("Type", "From", optwdg.SingleChoiceOptionEntry(
                self, "type", ['currently visible', 'from named filters'])),
            ("Type", "Filter", optwdg.CheckTreeOptionEntry(
                self, "used_filters")),
            ("Type", "Revert", optwdg.BoolOptionEntry(
                self, "reverted")),
            ("Representation", "True caption", optwdg.SimpleOptionEntry(
                self, "true_name", dostrip=True)),
            ("Representation", "False caption", optwdg.SimpleOptionEntry(
                self, "false_name", dostrip=True)),
            ])

    def on_value_change(self, code):
        if code in ['colname']:
            if not self.odata().colshortname:
                self.set_odata_entry('colshortname',
                                     self.odata().colname[:3].strip())

    def _active_entries(self, entry):
        if entry.member_name in ['used_filters']:
            if self.odata().type == "currently visible":
                return False
        return True

    def check_input(self):
        self.dt.is_valid_column_name(self.odata().colname,
                                     self.odata().colshortname)
        if self.odata().true_name == self.odata().false_name:
            raise Exception("True/False captions should not be equal")

    def ret_value(self):
        "-> new ColumnInfo"
        if self.odata().type == "from named filters":
            f_names = [k for k, v in self.odata().used_filters.items() if v]
            flts = [self.dt.proj.get_named_filter(name) for name in f_names]
        else:
            flts = copy.deepcopy(self.dt.used_filters)
        if self.odata().reverted:
            for f in flts:
                f.do_remove = not f.do_remove
        sql_fun = filt.Filter.compile_sql_line(flts)
        if len(sql_fun) > 0:
            # remove WHERE statement
            sql_fun = sql_fun[6:]
        else:
            sql_fun = '1'
        return bcol.ColumnInfo.build_bool_category(
                self.odata().colname,
                self.odata().colshortname,
                [self.odata().true_name, self.odata().false_name],
                sql_fun)


@qtcommon.hold_position
class NewTableFromVisible(SimpleAbstractDialog):
    def __init__(self, dt, parent=None):
        # data
        self.dt = dt
        super().__init__("New table from {}".format(self.dt.table_name),
                         parent)
        self.resize(400, 300)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.tablename = ""
        obj.include_source_id = False

    def _odata_init(self):
        i = 1
        while True:
            nm = "Table {}".format(i)
            try:
                self.dt.proj.is_valid_table_name(nm)
                break
            except:
                i += 1
        self.set_odata_entry("tablename", nm)

    def olist(self):
        return optview.OptionsList([
            ("New table", "Source table name", optwdg.SimpleOptionEntry(
                self, 'tablename', dostrip=True)),
            ("New table", "Include source id", optwdg.BoolOptionEntry(
                self, 'include_source_id')),
            ])

    def check_input(self):
        self.dt.proj.is_valid_table_name(self.odata().tablename)

    def ret_value(self):
        "-> TabModel"
        od = self.odata()
        cols = collections.OrderedDict()
        for c in self.dt.visible_columns:
            if c.name == 'id':
                if not od.include_source_id:
                    continue
                else:
                    cols['id'] = "id ({})".format(self.dt.table_name())
            else:
                cols[c.name] = c.name
        # data table
        newdt = derived_tabs.copy_view_table(
                od.tablename, self.dt, cols, self.dt.proj)
        return newdt


@qtcommon.hold_position
class ImportTablesDlg(SimpleAbstractDialog):
    def __init__(self, parent=None):
        super().__init__("Import table", parent)
        self.resize(400, 300)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.filename = ''
        obj.format = "plain text"

    def olist(self):
        flt = [('Excel files', ('xlsx',))]
        return optview.OptionsList([
            ("Import from", "Filename", optwdg.OpenFileOptionEntry(
                self, "filename", flt)),
            ("Import from", "Format", optwdg.SingleChoiceOptionEntry(
                self, "format", ["xlsx", "plain text"])),
            ])

    def on_value_change(self, code):
        if code == 'filename':
            if self.odata().filename[-5:] == '.xlsx':
                self.set_odata_entry('format', 'xlsx')
            elif self.odata().filename[-4:] == '.txt':
                self.set_odata_entry('format', 'plain text')

    def ret_value(self):
        return self.odata().filename, self.odata().format

    def check_input(self):
        from pathlib import Path
        my_file = Path(self.odata().filename)
        if not my_file.is_file():
            raise Exception("Invalid file name")


@qtcommon.hold_position
class OptionsDlg(SimpleAbstractDialog):
    def __init__(self, opts, parent=None):
        self.opts = opts
        super().__init__("Configuration", parent)
        self.resize(300, 400)

    def _default_odata(self, obj):
        obj.basic_font_size = 10
        obj.show_bool_as = 'icons'
        obj.real_numbers_prec = 6
        obj.external_xlsx_editor = ''
        obj.external_txt_editor = ''
        obj.open_recent_db_on_start = True

    def _odata_init(self):
        o = self.opts
        self.set_odata_entry('basic_font_size', o.basic_font_size)
        self.set_odata_entry('show_bool_as', o.show_bool_as)
        self.set_odata_entry('real_numbers_prec', o.real_numbers_prec)
        self.set_odata_entry('external_xlsx_editor', o.external_xlsx_editor)
        self.set_odata_entry('external_txt_editor', o.external_txt_editor)
        self.set_odata_entry('open_recent_db_on_start',
                             bool(o.open_recent_db_on_start))

    def olist(self):
        return optview.OptionsList([
            ("Main table", "Font size", optwdg.BoundedIntOptionEntry(
                self, "basic_font_size", minv=3)),
            ("Main table", "Boolean values as", optwdg.SingleChoiceOptionEntry(
                self, "show_bool_as", ['icons', 'codes', 'Yes/No'])),
            ("Main table", "Real number digits", optwdg.BoundedIntOptionEntry(
                self, "real_numbers_prec", minv=0)),
            ("External programs", "Xlsx editor", optwdg.OpenFileOptionEntry(
                self, "external_xlsx_editor", [])),
            ("External programs", "Text editor", optwdg.OpenFileOptionEntry(
                self, "external_txt_editor", [])),
            ("Behaviour", "Open recent db on start", optwdg.BoolOptionEntry(
                self, "open_recent_db_on_start")),
            ])

    def ret_value(self):
        od = copy.deepcopy(self.odata())
        need_view_update = not all([self.opts.__dict__[a] == od.__dict__[a]
                                    for a in ['basic_font_size',
                                              'show_bool_as',
                                              'real_numbers_prec']])
        for a in ['basic_font_size', 'show_bool_as', 'real_numbers_prec',
                  'external_xlsx_editor', 'external_txt_editor']:
            self.opts.__dict__[a] = od.__dict__[a]
        self.opts.open_recent_db_on_start = int(od.open_recent_db_on_start)
        return need_view_update
