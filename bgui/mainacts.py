from PyQt5 import QtWidgets, QtGui
from prog import basic
from bgui import dlgs
from bgui import qtcommon
from bgui import tview
from bgui import maincoms
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
        self.flow = mainwin.flow
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
        com = maincoms.ComNewDatabase(self.mainwin)
        self.flow.exec_command(com)


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
            com = maincoms.ComOpenDatabase(fname=filename[0])
            self.flow.exec_command(com)


class ActCloseDatabase(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Close database',
                         hotkey=QtGui.QKeySequence.Close)

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        com = maincoms.ComNewDatabase(self.mainwin)
        self.flow.exec_command(com)


class ActSave(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Save',
                         icon=':/save',
                         hotkey=QtGui.QKeySequence.Save)

    def isactive(self):
        return self.proj.sql.has_A

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
            self.saveto(fname)

    def saveto(self, fname):
        com = maincoms.ComSaveDB(self.mainwin, fname)
        self.flow.exec_command(com)


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
                comimp = dialog2.ret_value()
                com = maincoms.ComImport(self.mainwin, comimp)
                self.flow.exec_command(com)


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
        sz = self.mainwin.opts.basic_font_size + 2
        com = maincoms.ComChangeOpt(self.mainwin,
                                    {"basic_font_size": sz})
        self.flow.exec_command(com)


class ActDecreaseFont(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Decrease font',
                         hotkey=QtGui.QKeySequence.ZoomOut,
                         icon=':/zoomout')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        sz = self.mainwin.opts.basic_font_size - 2
        com = maincoms.ComChangeOpt(self.mainwin,
                                    {"basic_font_size": sz})
        self.flow.exec_command(com)


class ActToDataWidth(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Fit to data width',
                         icon=':/width')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        rw = self.aview().adjusted_width('data')
        com = maincoms.ComColumnWidth(self.mainwin, rw)
        self.flow.exec_command(com)


class ActToCaptionDataWidth(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Fit to data and caption width')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        rw = self.aview().adjusted_width('data/caption')
        com = maincoms.ComColumnWidth(self.mainwin, rw)
        self.flow.exec_command(com)


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
            v = dialog.ret_value()
            rw = {c.id: v for c in self.amodel().dt.all_columns}
            com = maincoms.ComColumnWidth(self.mainwin, rw)
            self.flow.exec_command(com)


class ActConfig(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Configuration',
                         icon=':/settings')

    def do(self):
        dialog = dlgs.OptionsDlg(self.mainwin.opts, self.mainwin)
        if dialog.exec_():
            ret = dialog.ret_value()
            com = maincoms.ComChangeOpt(self.mainwin, ret)
            self.flow.exec_command(com)


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
        com = maincoms.ComFoldRows(self.mainwin, 'all', True)
        self.flow.exec_command(com)


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
        com = maincoms.ComFoldRows(self.mainwin, 'all', False)
        self.flow.exec_command(com)


class ActToggleColoring(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Apply coloring',
                         checkable=True)

    def isactive(self):
        return self.amodel() is not None

    def ischecked(self):
        return self.amodel().use_coloring()

    def do(self):
        com = maincoms.ComToggleColoring(self.amodel())
        self.flow.exec_command(com)


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
            com = maincoms.ComSetColoring(self.amodel(), *ret)
            self.flow.exec_command(com)


class ActCollapseAll(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Collapse all categories')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        delim = ActCollapse.last_used_delimiter
        com = maincoms.ComCollapseCategories(
            self.amodel(), 'all', delim, True)
        self.flow.exec_command(com)


class ActRemoveCollapses(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Remove all collapses')

    def isactive(self):
        return self.amodel() is not None and\
                len(self.amodel().collapsed_categories_columns()) > 0

    def do(self):
        com = maincoms.ComRemoveCollapses(self.amodel())
        self.flow.exec_command(com)


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
            com = maincoms.ComCollapseCategories(
                    self.amodel(), r[2], r[1], r[0])
            self.flow.exec_command(com)
            self.last_used_delimiter = r[1]


class ActGroupRedundancies(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, 'Group redundancies')

    def isactive(self):
        return self.amodel() is not None

    def do(self):
        cn = self.amodel().dt.get_category_names()
        m = 'amean'
        com = maincoms.ComGroupCats(self.amodel(), cn, m)
        self.flow.exec_command(com)


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
        com = maincoms.ComGroupCats(self.amodel(), cats, method)
        self.flow.exec_command(com)


class ActUngroupAll(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Ungroup all",
                         icon=':/ungroup')

    def isactive(self):
        if self.amodel() is None:
            return False
        return self.amodel().has_groups()

    def do(self):
        com = maincoms.ComGroupCats(self.amodel(), [], 'amean')
        self.flow.exec_command(com)


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
            com = maincoms.ComAddFilter(self.amodel(), flt)
            self.flow.exec_command(com)


class ActRemoveAllFilters(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Remove all filters",
                         icon=":/unfilter")

    def isactive(self):
        if self.amodel() is None:
            return False
        return len(self.amodel().dt.used_filters) > 0

    def do(self):
        com = maincoms.ComRemAllFilters(self.amodel())
        self.flow.exec_command(com)


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
                    com = maincoms.ComConvertColumns(self.mainwin, ret)
                    self.flow.exec_command(com)
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
                    com = maincoms.ComChangeDictionaries(self.mainwin, ret)
                    self.flow.exec_command(com)
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
            com = maincoms.ComAddTable(self.mainwin, dt)
            self.flow.exec_command(com)


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
                com = maincoms.ComAddTable(self.mainwin, dt)
                self.flow.exec_command(com)
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
            # self.proj.remove_table(self.amodel().dt.table_name())
            # if len(self.mainwin.models) == 1:
            #     self.mainwin._set_active_model(None)
            #     ind = 0
            # else:
            #     ind = self.mainwin.models.index(self.amodel())
            # self.mainwin.models.pop(ind)
            # self.mainwin.wtab.removeTab(ind)
            com = maincoms.ComRemoveTable(self.mainwin,
                                          self.mainwin.active_index())
            self.flow.exec_command(com)
        except Exception as e:
            qtcommon.message_exc(self.mainwin, e=e)


class ActUndo(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Undo", icon=":/undo",
                         hotkey=QtGui.QKeySequence.Undo)

    def isactive(self):
        return self.flow.can_undo()

    def do(self):
        self.flow.undo_prev()


class ActRedo(MainAct):
    def __init__(self, mainwin):
        super().__init__(mainwin, "Redo", icon=":/redo",
                         hotkey=QtGui.QKeySequence.Redo)

    def isactive(self):
        return self.flow.can_redo()

    def do(self):
        self.flow.exec_next()
