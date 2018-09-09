import functools
from PyQt5 import QtWidgets, QtGui, QtCore
from bdata import derived_tabs
from bgui import dlgs
from bgui import tmodel
from bgui import tview
from bgui import docks
from bgui import qtcommon
from prog import basic
from fileproc import export


class MainWindow(QtWidgets.QMainWindow):
    "application main window"
    active_model_changed = QtCore.pyqtSignal()
    active_model_repr_changed = QtCore.pyqtSignal()

    def __init__(self, proj):
        'proj - prog.projroot.ProjectDB'
        super().__init__()
        QtWidgets.qApp.aboutToQuit.connect(self._on_quit)
        # init position (will be changed by opts data)
        self.resize(800, 600)
        self.setGeometry(QtWidgets.QStyle.alignedRect(
            QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
            self.size(), QtWidgets.qApp.desktop().availableGeometry()))

        # data
        self.proj = proj
        self.models = []
        self.active_model = None
        self.reload_options(proj.opts)

        # interface
        self.ui()

        # Load data
        self.reset_title()
        filename = self.opts.default_project_filename()
        if filename is not None:
            self._load_database(filename)

        # restore
        try:
            state, geom = self.opts.mainwindow_state()
            self.restoreState(state)
            self.restoreGeometry(geom)
        except Exception as e:
            basic.ignore_exception(e)

    def ui(self):
        # =========== central widget
        self.wtab = QtWidgets.QTabWidget(self)
        self.wtab.currentChanged.connect(self._tab_changed)
        self.tabframes = []
        self.setCentralWidget(self.wtab)

        # ============== Menu
        menubar = self.menuBar()

        # ============ Filemenu
        self.filemenu = qtcommon.BMenu('File', self, menubar)
        # new db
        self.filemenu.add_action('New database', self._act_newdb,
                                 hotkey=QtGui.QKeySequence.New)
        # open db
        self.filemenu.add_action('Open database', self._act_open_database,
                                 hotkey=QtGui.QKeySequence.Open)
        # open recent
        self.filemenu.add_menu(QtWidgets.QMenu('Open recent database', self),
                               menufun=self._recentmenu)
        # close
        self.filemenu.add_action('Close database', self._close_database,
                                 vis=self.has_model,
                                 hotkey=QtGui.QKeySequence.Close)
        self.filemenu.addSeparator()
        # save, save as
        self.filemenu.add_action('Save', self._act_save,
                                 vis=self.proj.need_save,
                                 hotkey=QtGui.QKeySequence.Save)
        self.filemenu.add_action('Save as...', self._act_saveas)
        self.filemenu.addSeparator()
        # export, import
        self.filemenu.add_action('Export tables...', self._act_export,
                                 vis=self.has_model)
        self.filemenu.add_action('Import tables...', self._act_import_table)
        self.filemenu.addSeparator()
        # config
        self.filemenu.add_action('Configuration', self._act_opts)
        self.filemenu.addSeparator()
        # exit
        self.filemenu.add_action('Exit', QtWidgets.qApp.quit,
                                 hotkey=QtGui.QKeySequence.Close)

        # --- View
        self.viewmenu = qtcommon.BMenu('View', self, menubar)
        self.viewmenu.aboutToShow.connect(self._viewmenu_enabled)
        # zoom
        self.viewmenu.add_action('Increase font',
                                 functools.partial(self._act_zoom, 2),
                                 vis=self.has_model)
        self.viewmenu.add_action('Decrease font',
                                 functools.partial(self._act_zoom, -2),
                                 vis=self.has_model)
        self.viewmenu.addSeparator()
        # fold/unfold
        self.fold_rows_action = self.viewmenu.add_action(
                'Fold all groups', self._act_fold_all_rows,
                vis=self.has_model)
        self.unfold_rows_action = self.viewmenu.add_action(
                'Unfold all groups', self._act_unfold_all_rows,
                vis=self.has_model)
        self.viewmenu.addSeparator()
        # color scheme
        self.apply_color_action = self.viewmenu.add_action(
                'Apply coloring', self._act_apply_color,
                vis=self.has_model)
        self.viewmenu.add_action('Set coloring...', self._act_set_coloring,
                                 vis=self.has_model)

        # --- Columns
        self.columnsmenu = qtcommon.BMenu('Columns', self, menubar)
        # collapse
        self.columnsmenu.add_action('Collapse all categories',
                                    self._act_collapse_all, self.has_model)
        self.columnsmenu.add_action('Remove all collapses',
                                    self._act_collapse_all, self.has_model)
        self.columnsmenu.add_action('Collapse ...', self._act_collapse,
                                    self.has_model)
        # add columns
        self.columnsmenu.addSeparator()
        self.columnsmenu.add_action('New boolean category...',
                                    self._act_new_bool_column, self.has_model)
        self.columnsmenu.add_action('New enum category...',
                                    self._act_new_enum_column, self.has_model)

        # --- Rows
        self.rowsmenu = qtcommon.BMenu('Rows', self, menubar)
        # group/ungroup
        self.rowsmenu.add_action('Group redundancies',
                                 self._act_group_by_redundancy,
                                 self.has_model)
        self.rowsmenu.add_action('Ungroup all',
                                 self._act_ungroup_rows, self.has_model)
        self.rowsmenu.add_action('Group rows...',
                                 self._act_group_rows, self.has_model)

        # filtering
        self.rowsmenu.addSeparator()
        self.rowsmenu.add_action('Add filter...',
                                 self._act_filter, self.has_model)
        self.rowsmenu.add_action('Remove all filters',
                                 self._act_rem_filters, self.has_model)

        # --- Tables
        self.tablesmenu = qtcommon.BMenu('Data', self, menubar)

        # tables and columns info
        self.tablesmenu.add_action("Tables...", self._act_tab_col,
                                   lambda: len(self.models) > 0)
        # dictionaries
        self.tablesmenu.add_action("Dictionaries...", self._act_dictinfo)

        # new table
        self.tablesmenu.addSeparator()
        self.tablesmenu.add_action('New table from visible...',
                                   self._act_table_from_visible,
                                   self.has_model)

        # join tables
        self.tablesmenu.add_action('Join tables...', self._act_join_tables,
                                   lambda: len(self.models) > 1)

        # remove active table
        self.tablesmenu.addSeparator()
        self.tablesmenu.add_action("Remove active table",
                                   self._act_remove_table, self.has_model)

        # --- Show dock windows
        winmenu = menubar.addMenu("Show")
        self.dock_color = docks.ColorDockWidget(self, winmenu)
        self.dock_filters = docks.FiltersDockWidget(self, winmenu)
        self.dock_colinfo = docks.ColumnInfoDockWidget(self, winmenu)

        # --- About
        self.aboutmenu = qtcommon.BMenu('About', self, menubar)

    # =============== Actions
    def _tab_changed(self, index):
        if index >= 0:
            self._set_active_model(index)
        else:
            self._set_active_model(None)

    def _recentmenu(self, menu):
        menu.clear()
        menu.setEnabled(len(self.opts.recent_db) > 0)
        for f in self.opts.recent_db:
            act = QtWidgets.QAction(f, self)
            act.triggered.connect(functools.partial(self._load_database, f))
            menu.addAction(act)
        act = QtWidgets.QAction('Clear', self)
        act.triggered.connect(self.opts.recent_db.clear)
        menu.addSeparator()
        menu.addAction(act)

    def _rowsmenu_enabled(self):
        enabled = self.active_model is not None
        for m in self.rowsmenu.actions():
            m.setEnabled(enabled)
        if not enabled:
            return

        # remove filters visible
        has_flt = self.active_model.n_filters() > 0
        self.rem_all_filter_action.setEnabled(has_flt)
        # ungroup all visible
        has_groups = self.active_model.has_groups()
        self.ungroup_rows_action.setEnabled(has_groups)

    def _viewmenu_enabled(self):
        if self.has_model():
            # set checks for fold/unfold
            self.fold_rows_action.setChecked(
                self.active_model._unfolded_groups is False)
            self.unfold_rows_action.setChecked(
                self.active_model._unfolded_groups is True)
            # set checks for coloring
            self.apply_color_action.setChecked(
                self.active_model.use_coloring())

    def _act_newdb(self):
        self._close_database()

    def _act_open_database(self):
        flt = "Databases (*.db, *.sqlite)(*.db *.sqlite);;Any files(*)"
        filename = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open database", filter=flt)
        if filename[0]:
            self._load_database(fname=filename[0])

    def _act_zoom(self, delta):
        self.opts.basic_font_size += delta
        self.reload_options(self.opts)

    def _act_fold_all_rows(self):
        self.active_model.unfold_all_rows(False)

    def _act_unfold_all_rows(self):
        self.active_model.unfold_all_rows(True)

    def _act_filter(self):
        from bgui import filtdlg
        dialog = filtdlg.EditFilterDialog(None, self.active_model.dt,
                                          None, self)
        if dialog.exec_():
            flt = dialog.ret_value()
            self.active_model.add_filter(flt)
            self.update()

    def _act_rem_filters(self):
        self.active_model.rem_all_filters()
        self.update()

    def _act_group_rows(self):
        dialog = dlgs.GroupRowsDlg(
            self.active_model.dt.get_category_names(), self)
        if dialog.exec_():
            r = dialog.ret_value()
            self.active_model.group_rows(r[1], r[0])
            self.update()

    def _act_group_by_redundancy(self):
        self.active_model.group_rows(
                self.active_model.dt.get_category_names(), 'amean')
        self.update()

    def _act_ungroup_rows(self):
        self.active_model.group_rows([])
        self.update()

    def _act_collapse_all(self):
        try:
            delim = self.__last_collapse_delimiter
        except:
            delim = '-'
        if self.active_model.collapse_categories('all', True, delim):
            self.update()

    def _act_uncollapse_all(self):
        if self.active_model.remove_collapsed('all', True):
            self.update()

    def _act_collapse(self):
        dialog = dlgs.CollapseColumnsDlg(
            self.active_model.dt.get_category_names(), self)
        if dialog.exec_():
            r = dialog.ret_value()
            a = self.active_model.collapse_categories(r[2], r[0], r[1])
            if a:
                self.__last_collapse_delimiter = r[1]
                self.update()

    def _act_export(self):
        dialog = dlgs.ExportTablesDlg(self)
        if dialog.exec_():
            actview = self.tabframes[self.models.index(self.active_model)]
            export.model_export(self.active_model.dt, dialog.ret_value(),
                                self.active_model, actview)

    def _act_set_coloring(self):
        clist = self.active_model.all_column_names()
        dialog = dlgs.RowColoringDlg(clist, self)
        if dialog.exec_():
            ret = dialog.ret_value()
            self.active_model.set_coloring(ret[0], ret[1], ret[2])

    def _act_apply_color(self):
        self.active_model.switch_coloring_mode()

    def _act_new_bool_column(self):
        # TODO
        pass
        # dialog = dlgs.NewBoolColumn(self.active_model.dt, self)
        # if dialog.exec_():
        #     newcol = dialog.ret_value()
        #     self.active_model.dt.add_column(newcol, None, True)
        #     self.active_model.update()

    def _act_new_enum_column(self):
        # TODO
        pass

    def _act_table_from_visible(self):
        dialog = dlgs.NewTableFromVisible(self.active_model.dt, self)
        if dialog.exec_():
            dt = dialog.ret_value()
            self.proj.add_table(dt)
            newmodel = tmodel.TabModel(dt)
            index = self.add_model(newmodel)
            self.wtab.setCurrentIndex(index)

    def _act_remove_table(self):
        i = self.active_index()
        mod = self.models[i]
        try:
            self.proj.remove_table(mod.table_name())
            self.models.pop(i)
            self.wtab.removeTab(i)
        except Exception as e:
            qtcommon.message_exc(self, e=e)

    def _act_join_tables(self):
        from bgui import joindlg
        dialog = joindlg.JoinTablesDialog(self.active_model.dt, self)
        if dialog.exec_():
            name, tabentries = dialog.ret_value()
            dt = derived_tabs.join_table(name, tabentries, self.proj)
            self.proj.add_table(dt)
            newmodel = tmodel.TabModel(dt)
            index = self.add_model(newmodel)
            self.wtab.setCurrentIndex(index)

    def _act_import_table(self):
        from bgui import importdlgs
        dialog = dlgs.ImportTablesDlg()
        if dialog.exec_():
            fname, frmt = dialog.ret_value()
            if frmt == "plain text":
                dialog2 = importdlgs.ImportPlainText(self.proj, fname, self)
            elif frmt == "xlsx":
                dialog2 = importdlgs.ImportXlsx(self.proj, fname, self)
            else:
                raise Exception("Unknow format {}".format(frmt))
            if dialog2.exec_():
                name, tab, cols = dialog2.ret_value()
                newdt = derived_tabs.explicit_table(name, cols, tab, self.proj)
                self.proj.add_table(newdt)
                newmodel = tmodel.TabModel(newdt)
                index = self.add_model(newmodel)
                self.wtab.setCurrentIndex(index)

    def _act_tab_col(self):
        pass

    def _act_dictinfo(self):
        from bgui import dictdlg
        dialog = dictdlg.DictInformation(self.proj, self)
        if dialog.exec_():
            ret = dialog.ret_value()
            self.proj.change_dictionaries(ret[0], shrink=ret[1]['Shrink'])
            self.update()

    def _on_quit(self):
        self.opts.set_mainwindow_state(self.saveState(), self.saveGeometry())
        self.opts.save()

    def _act_opts(self):
        dialog = dlgs.OptionsDlg(self.opts, self)
        if dialog.exec_():
            dialog.ret_value()
            self.opts.save()
            self.reload_options(self.opts)

    def _act_saveas(self):
        flt = "Databases (*.db, *.sqlite)(*.db *.sqlite)"
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save database as", self.proj.curdir(), flt)
        if filename[0]:
            try:
                self.proj.relocate_and_commit_all_changes(filename[0])
                self._set_actual_file(filename[0])
            except Exception as e:
                qtcommon.message_exc(self, "Save error", e=e)

    def _act_save(self):
        try:
            self.proj.commit_all_changes()
        except Exception as e:
            qtcommon.message_exc(self, "Save error", e=e)

    # ============== Procedures
    def _load_database(self, fname):
        import pathlib
        if not fname:
            return
        try:
            if not pathlib.Path(fname).is_file():
                raise Exception("File doesn't exist.")
            self._close_database()
            self.proj.set_main_database(fname)
            self._init_project()
            self._set_actual_file(fname)
        except Exception as e:
            m = 'Failed to load database from "{}". '.format(fname)
            qtcommon.message_exc(self, "Load error", text=m, e=e)

    def _set_actual_file(self, fname):
        self.opts.add_db_path(fname)
        self.reset_title()

    def reset_title(self):
        self.setWindowTitle(self.proj._curname + " - BioStat Analyser")

    def _close_database(self):
        self.proj.close_main_database()
        self.active_model = None
        self.models = []
        self.wtab.clear()
        self.tabframes = []
        self.reset_title()

    def _init_project(self):
        self.models = []
        # models
        for t in self.proj.data_tables:
            self.models.append(tmodel.TabModel(t))
        if self.models:
            self.active_model = self._set_active_model(0)
        self._init_widgets()

    def _init_widgets(self):
        self.tabframes = []
        for m in self.models:
            self.tabframes.append(tview.TableView(m, self.wtab))
        for f in self.tabframes:
            self.wtab.addTab(f, f.table_name())

    def has_model(self):
        return self.active_model is not None

    def active_index(self):
        return self.models.index(self.active_model)

    def add_model(self, newmodel):
        self.models.append(newmodel)
        self.tabframes.append(tview.TableView(newmodel, self.wtab))
        # add {} to show that this is a derived model
        self.wtab.addTab(self.tabframes[-1],
                         '{' + self.tabframes[-1].table_name() + '}')
        return len(self.models) - 1

    def _forward_repr_changed(self, a, b):
        self.active_model_repr_changed.emit()

    def _set_active_model(self, i):
        if self.active_model is not None:
            self.active_model.repr_updated.disconnect(
                    self._forward_repr_changed)
        if i is not None and i < len(self.models):
            self.active_model = self.models[i]
            self.active_model_changed.emit()
            self.active_model.repr_updated.connect(
                    self._forward_repr_changed)
            self.update()
        else:
            self.active_model = None
            self.active_model_changed.emit()

    def update(self):
        if self.active_model:
            self.active_model.update()

    def view_update(self):
        if self.active_model:
            self.active_model.view_update()

    def reload_options(self, opts):
        from bgui import cfg

        self.opts = opts
        cfg.ViewConfig.set_real_precision(opts.real_numbers_prec)
        cfg.ViewConfig.get()._basic_font_size = opts.basic_font_size
        cfg.ViewConfig.get()._show_bool =\
            {'icons': cfg.ViewConfig.BOOL_AS_ICONS,
             'codes': cfg.ViewConfig.BOOL_AS_CODES,
             'Yes/No': cfg.ViewConfig.BOOL_AS_YESNO}[opts.show_bool_as]
        cfg.ViewConfig.get().refresh()
        self.view_update()
