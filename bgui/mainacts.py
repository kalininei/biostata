from PyQt5 import QtWidgets, QtGui
from prog import basic
from bgui import dlgs
from bgui import qtcommon
from bgui import tview
from bgui import tmodel
from bdata import derived_tabs
from fileproc import export


class MainAct(QtWidgets.QAction):
    def __init__(self, mainwin, title,
                 icon=None, hotkey=None, checkable=False):
        super().__init__(title, mainwin)

        if icon is not None:
            self.setIcon(QtGui.QIcon(icon))

        if hotkey is not None:
            self.setShortcut(hotkey)

        self.setCheckable(checkable)

        self.triggered.connect(lambda: self.do())

        self.name = title
        self.mainwin = mainwin
        self.proj = mainwin.proj
        self.amodel = lambda: mainwin.active_model
        self.aview = lambda: mainwin.active_tview()

    def isactive(self):
        return True

    def ischecked(self):
        return False

    def do(self):
        pass


class ActNewDatabase(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'New database',
                         icon=':/new',
                         hotkey=QtGui.QKeySequence.New)

    def do(self):
        self.mainwin._close_database()


class ActQuit(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Quit',
                         hotkey=QtGui.QKeySequence.Quit)

    def do(self):
        QtWidgets.qApp.quit()


class ActOpenDatabase(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Open database',
                         icon=':/open',
                         hotkey=QtGui.QKeySequence.Open)

    def do(self):
        flt = "Databases (*.db, *.sqlite)(*.db *.sqlite);;Any files(*)"
        filename = QtWidgets.QFileDialog.getOpenFileName(
                self.mainwin, "Open database", filter=flt)
        if filename[0]:
            self.mainwin._load_database(fname=filename[0])


class ActCloseDatabase(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Close database',
                         hotkey=QtGui.QKeySequence.Close)

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        self.mainwin._close_database()


class ActSave(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Save',
                         icon=':/save',
                         hotkey=QtGui.QKeySequence.Save)

    def isactive(self):
        return self.proj.need_save()

    def do(self):
        self.mainwin.save()


class ActSaveAs(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Save as...',
                         hotkey=QtGui.QKeySequence.SaveAs)

    def do(self):
        flt = "Databases (*.db, *.sqlite)(*.db *.sqlite)"
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.mainwin, "Save database as", self.proj.curdir(), flt)
        if fname:
            self.mainwin.saveto(fname)


class ActImport(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Import tables...',
                         icon=':/import')

    def do(self):
        from bgui import importdlgs
        dialog = dlgs.ImportTablesDlg(self.mainwin)
        if dialog.exec_():
            fname, frmt = dialog.ret_value()
            try:
                if frmt == "plain text":
                    dialog2 = importdlgs.ImportPlainText(
                        self.proj, fname,
                        lambda: self.mainwin.require_editor('text'),
                        self.mainwin)
                elif frmt == "xlsx":
                    dialog2 = importdlgs.ImportXlsx(
                        self.proj, fname,
                        lambda: self.mainwin.require_editor('xlsx'),
                        self.mainwin)
                else:
                    raise Exception("Unknow format {}".format(frmt))
            except Exception as e:
                qtcommon.message_exc(self.mainwin, "Import error", e=e)
                return
            if dialog2.exec_():
                name, tab, cols = dialog2.ret_value()
                newdt = derived_tabs.explicit_table(name, cols, tab, self.proj)
                self.proj.add_table(newdt)
                newmodel = tmodel.TabModel(newdt)
                self.mainwin.add_model(newmodel, True)


class ActExport(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Export tables...',
                         icon=':/export')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        dialog = dlgs.ExportTablesDlg(self.mainwin)
        if dialog.exec_():
            export.model_export(self.amodel().dt,
                                dialog.ret_value(),
                                self.amodel(), self.aview())


class ActExternalXlsxView(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Open table in external viewer',
                         icon=':/excel')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        import subprocess
        try:
            # temporary filename
            fname = export.get_unused_tmp_file('xlsx')

            # choose editor
            prog = self.mainwin.require_editor('xlsx')
            if not prog:
                return
            # export to a temporary
            opts = basic.CustomObject()
            opts.filename = fname
            opts.with_caption = True
            opts.with_id = True
            opts.format = 'xlsx'
            opts.numeric_enums = False
            opts.grouped_categories = 'None'
            opts.with_formatting = True
            export.model_export(self.amodel().dt,
                                opts,
                                self.amodel(), self.aview())
            # open with editor
            path = ' '.join([prog, fname])
            subprocess.Popen(path.split())
        except Exception as e:
            qtcommon.message_exc(self.mainwin, "Open error", e=e)


class ActIncreaseFont(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Increase font',
                         hotkey=QtGui.QKeySequence.ZoomIn,
                         icon=':/zoomin')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        self.mainwin.zoom_font(2)


class ActDecreaseFont(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Decrease font',
                         hotkey=QtGui.QKeySequence.ZoomOut,
                         icon=':/zoomout')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        self.mainwin.zoom_font(-2)


class ActToDataWidth(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Fit to data width',
                         icon=':/width')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        self.aview().width_adjust('data')


class ActToCaptionDataWidth(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Fit to data and caption width')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        self.aview().width_adjust('data/caption')


class ActToConstantWidth(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Set constant width...')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        dv = self.aview().columnWidth(0)
        mv = tview.TableView._minimum_column_width
        dialog = dlgs.InputInteger("Enter width", self.mainwin,
                                   dv, minvalue=mv)
        if dialog.exec_():
            self.aview().width_adjust(dialog.ret_value())


class ActConfig(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Configuration',
                         icon=':/settings')

    def do(self):
        dialog = dlgs.OptionsDlg(self.mainwin.opts, self.mainwin)
        if dialog.exec_():
            dialog.ret_value()
            self.mainwin.opts.save()
            self.mainwin.reload_options(self.mainwin.opts)


class ActFoldAll(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Fold all groups',
                         icon=':/fold')

    def isactive(self):
        if self.amodel() is None:
            return False
        if not self.amodel().has_groups():
            return False
        return self.amodel()._unfolded_groups is not False

    def do(self):
        self.amodel().unfold_all_rows(False)


class ActUnfoldAll(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Unfold all groups',
                         icon=':/unfold')

    def isactive(self):
        if self.amodel() is None:
            return False
        if not self.amodel().has_groups():
            return False
        return self.amodel()._unfolded_groups is not True

    def do(self):
        self.amodel().unfold_all_rows(True)


class ActToggleColoring(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Apply coloring',
                         checkable=True)

    def isactive(self):
        return self.amodel() is not None

    def ischecked(self):
        return self.amodel().use_coloring()

    def do(self):
        self.amodel().switch_coloring_mode()


class ActSetColoring(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Set coloring...')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        clist = self.amodel().all_column_names()
        dialog = dlgs.RowColoringDlg(clist, self.mainwin)
        if dialog.exec_():
            ret = dialog.ret_value()
            self.amodel().set_coloring(ret[0], ret[1], ret[2])


class ActCollapseAll(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Collapse all categories')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        delim = ActCollapse.last_used_delimiter
        if self.amodel().collapse_categories('all', True, delim):
            self.mainwin.update()


class ActRemoveCollapses(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Remove all collapses')

    def isactive(self):
        return self.amodel() is not None and\
                len(self.amodel().collapsed_categories_columns()) > 0

    def do(self):
        if self.amodel().remove_collapsed('all', True):
            self.mainwin.update()


class ActCollapse(MainAct):
    last_used_delimiter = '-'

    def __init__(self, mainwin):
        super().__init__(mainwin, 'Collapse...')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        dialog = dlgs.CollapseColumnsDlg(
            self.amodel().dt.get_category_names(), self.mainwin)
        if dialog.exec_():
            r = dialog.ret_value()
            a = self.amodel().collapse_categories(r[2], r[0], r[1])
            if a:
                self.last_used_delimiter = r[1]
                self.mainwin.update()


class ActGroupRedundancies(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Group redundancies')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        self.amodel().group_rows(
                self.amodel().dt.get_category_names(), 'amean')
        self.mainwin.update()


class ActGroup(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Group rows...",
                         icon=':/group')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        dialog = dlgs.GroupRowsDlg(
            self.amodel().dt.get_category_names(), self.mainwin)
        if dialog.exec_():
            r = dialog.ret_value()
            self.group_cats(r[1], r[0])

    def group_cats(self, cats, method):
        self.amodel().group_rows(cats, method)
        self.mainwin.update()


class ActUngroupAll(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Ungroup all",
                         icon=':/ungroup')

    def isactive(self):
        if self.amodel() is None:
            return False
        return self.amodel().has_groups()

    def do(self):
        self.amodel().group_rows([])
        self.mainwin.update()


class ActAddFilter(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Add filter...",
                         icon=":/filter")

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        from bgui import filtdlg
        dialog = filtdlg.EditFilterDialog(None, self.amodel().dt,
                                          None, self.mainwin)
        if dialog.exec_():
            flt = dialog.ret_value()
            self.amodel().add_filter(flt)
            self.mainwin.update()


class ActRemoveAllFilters(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Remove all filters",
                         icon=":/unfilter")

    def isactive(self):
        if self.amodel() is None:
            return False
        return len(self.amodel().dt.used_filters) > 0

    def do(self):
        self.amodel().rem_all_filters()
        self.mainwin.update()


class ActTabColInfo(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Tables && columns...")

    def isactive(self):
        return len(self.mainwin.models) > 0

    def do(self):
        from bgui import colinfodlg
        try:
            dialog = colinfodlg.TablesInfo(self.proj, self.mainwin)
            if dialog.exec_():
                ret = dialog.ret_value()
                if not ret:
                    return
                else:
                    for r in ret:
                        r.apply()
                    self.mainwin.update()
        except Exception as e:
            qtcommon.message_exc(self.mainwin, "Error", e=e)
            self.mainwin.update()


class ActDictInfo(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Dictionaries...")

    def do(self):
        from bgui import dictdlg
        try:
            dialog = dictdlg.DictInformation(self.proj, self.mainwin)
            if dialog.exec_():
                ret = dialog.ret_value()
                if ret:
                    self.proj.change_dictionaries(ret)
                    self.mainwin.update()
        except Exception as e:
            qtcommon.message_exc(self.mainwin, "Error", e=e)
            self.mainwin.update()


class ActCopyTableVis(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'New table from visible...',
                         icon=':/copy')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        dialog = dlgs.NewTableFromVisible(self.amodel().dt, self.mainwin)
        if dialog.exec_():
            dt = dialog.ret_value()
            self.proj.add_table(dt)
            newmodel = tmodel.TabModel(dt)
            self.mainwin.add_model(newmodel)


class ActJoinTables(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Join tables...",
                         icon=":/join")

    def isactive(self):
        return len(self.mainwin.models) > 1

    def do(self):
        from bgui import joindlg
        dialog = joindlg.JoinTablesDialog(self.amodel().dt, self.mainwin)
        if dialog.exec_():
            try:
                name, tabentries = dialog.ret_value()
                dt = derived_tabs.join_table(name, tabentries, self.proj)
                self.proj.add_table(dt)
                newmodel = tmodel.TabModel(dt)
                self.mainwin.add_model(newmodel, True)
            except Exception as e:
                qtcommon.message_exc(self.mainwin, 'Join error', e=e)


class ActRemoveActiveTable(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Remove active table",
                         icon=":/remove")

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        try:
            self.proj.remove_table(self.amodel().dt.table_name())
            if len(self.mainwin.models) == 1:
                self.mainwin._set_active_model(None)
                ind = 0
            else:
                ind = self.mainwin.models.index(self.amodel())
            self.mainwin.models.pop(ind)
            self.mainwin.wtab.removeTab(ind)
        except Exception as e:
            qtcommon.message_exc(self.mainwin, e=e)
