import functools
from PyQt5 import QtWidgets, QtGui, QtCore
from bdata import projroot
from bdata import derived_tabs
from bgui import dlgs
from bgui import tmodel
from bgui import tview
from bgui import docks
from bgui import qtcommon
from fileproc import export


class MainWindow(QtWidgets.QMainWindow):
    "application main window"
    active_model_changed = QtCore.pyqtSignal()
    active_model_repr_changed = QtCore.pyqtSignal()

    def __init__(self, proj=None):
        super().__init__()
        self.setWindowTitle("BioStat Analyser")
        # =========== data
        self.proj = None
        self.models = []
        self.active_model = None

        # =========== central widget
        self.wtab = QtWidgets.QTabWidget(self)
        self.wtab.currentChanged.connect(self._tab_changed)
        self.tabframes = []
        self.setCentralWidget(self.wtab)

        # ============== Menu
        menubar = self.menuBar()

        # --- File
        self.filemenu = menubar.addMenu('File')
        self.filemenu.aboutToShow.connect(self._filemenu_enabled)
        # Open db
        open_action = QtWidgets.QAction("Open database...", self)
        open_action.triggered.connect(self._act_open_database)
        self.filemenu.addAction(open_action)
        # Exports
        self.filemenu.addSeparator()
        self.export_action = QtWidgets.QAction("Export tables...", self)
        self.export_action.triggered.connect(self._act_export)
        self.filemenu.addAction(self.export_action)
        # Exit
        self.filemenu.addSeparator()
        exit_action = QtWidgets.QAction('Exit', self)
        exit_action.setShortcut(QtGui.QKeySequence.Close)
        exit_action.triggered.connect(QtWidgets.qApp.quit)
        self.filemenu.addAction(exit_action)

        # --- Project
        self.projectmenu = menubar.addMenu('Project')
        self.projectmenu.aboutToShow.connect(self._projectmenu_enabled)

        # import table
        import_table = QtWidgets.QAction("Import table...", self)
        import_table.triggered.connect(self._act_import_table)
        self.projectmenu.addAction(import_table)

        # -- Edit actions
        self.projectmenu.addSeparator()
        # tables and columns
        tables_columns_info = QtWidgets.QAction("Tables && Columns...", self)
        tables_columns_info.triggered.connect(self._act_tab_col)
        self.projectmenu.addAction(tables_columns_info)
        # dictionaries
        dictionaries_info = QtWidgets.QAction("Dictionaries...", self)
        dictionaries_info.triggered.connect(self._act_dictinfo)
        self.projectmenu.addAction(dictionaries_info)

        # --- View
        self.viewmenu = menubar.addMenu('View')
        self.viewmenu.aboutToShow.connect(self._viewmenu_enabled)
        # zoom
        zoomin_act = QtWidgets.QAction('Increase font', self)
        zoomin_act.triggered.connect(functools.partial(
                self._act_zoom, 2))
        self.viewmenu.addAction(zoomin_act)
        zoomout_act = QtWidgets.QAction('Decrease font', self)
        zoomout_act.triggered.connect(functools.partial(
                self._act_zoom, -2))
        self.viewmenu.addAction(zoomout_act)
        # fold/unfold
        self.viewmenu.addSeparator()
        self.fold_rows_action = QtWidgets.QAction('Fold all groups', self)
        self.fold_rows_action.setCheckable(True)
        self.fold_rows_action.triggered.connect(self._act_fold_all_rows)
        self.viewmenu.addAction(self.fold_rows_action)
        self.unfold_rows_action = QtWidgets.QAction('Unfold all groups', self)
        self.unfold_rows_action.setCheckable(True)
        self.unfold_rows_action.triggered.connect(self._act_unfold_all_rows)
        self.viewmenu.addAction(self.unfold_rows_action)
        # color scheme
        self.viewmenu.addSeparator()
        self.apply_color_action = QtWidgets.QAction('Apply coloring', self)
        self.apply_color_action.setCheckable(True)
        self.apply_color_action.triggered.connect(self._act_apply_color)
        self.viewmenu.addAction(self.apply_color_action)
        self.set_color_action = QtWidgets.QAction('Set coloring...', self)
        self.set_color_action.triggered.connect(self._act_set_coloring)
        self.viewmenu.addAction(self.set_color_action)

        # --- Columns
        self.columnsmenu = menubar.addMenu('Columns')
        self.columnsmenu.aboutToShow.connect(self._columnsmenu_enabled)
        # collapse
        collapse_cats_action = QtWidgets.QAction(
                'Collapse all categories', self)
        collapse_cats_action.triggered.connect(self._act_collapse_all)
        self.columnsmenu.addAction(collapse_cats_action)
        self.uncollapse_cats_action = QtWidgets.QAction(
                'Remove all collapses', self)
        self.uncollapse_cats_action.triggered.connect(self._act_uncollapse_all)
        self.columnsmenu.addAction(self.uncollapse_cats_action)
        collapse_menu_action = QtWidgets.QAction(
                'Collapse ...', self)
        collapse_menu_action.triggered.connect(self._act_collapse)
        self.columnsmenu.addAction(collapse_menu_action)
        # add columns
        self.columnsmenu.addSeparator()
        column_by_filter_action = QtWidgets.QAction(
                'New boolean category...', self)
        column_by_filter_action.triggered.connect(self._act_new_bool_column)
        self.columnsmenu.addAction(column_by_filter_action)
        enum_column_action = QtWidgets.QAction(
                'New enum category...', self)
        enum_column_action.triggered.connect(self._act_new_enum_column)
        self.columnsmenu.addAction(enum_column_action)

        # --- Rows
        self.rowsmenu = menubar.addMenu('Rows')
        self.rowsmenu.aboutToShow.connect(self._rowsmenu_enabled)
        # group/ungroup
        group_by_redundancy_action = QtWidgets.QAction(
                'Group redundancies', self)
        group_by_redundancy_action.triggered.connect(
                self._act_group_by_redundancy)
        self.rowsmenu.addAction(group_by_redundancy_action)
        self.ungroup_rows_action = QtWidgets.QAction('Ungroup all', self)
        self.ungroup_rows_action.triggered.connect(self._act_ungroup_rows)
        self.rowsmenu.addAction(self.ungroup_rows_action)
        group_rows_action = QtWidgets.QAction('Group rows...', self)
        group_rows_action.triggered.connect(self._act_group_rows)
        self.rowsmenu.addAction(group_rows_action)

        # filtering
        self.rowsmenu.addSeparator()
        filter_action = QtWidgets.QAction('Add Filter...', self)
        filter_action.triggered.connect(self._act_filter)
        self.rowsmenu.addAction(filter_action)

        self.rem_all_filter_action = QtWidgets.QAction(
                'Remove all filters', self)
        self.rem_all_filter_action.triggered.connect(
                lambda: (self.active_model.rem_all_filters(),
                         self.active_model.update()))
        self.rowsmenu.addAction(self.rem_all_filter_action)

        # --- Tables
        self.tablesmenu = menubar.addMenu('Tables')
        self.tablesmenu.aboutToShow.connect(self._tablesmenu_enabled)

        # new table
        table_from_visible = QtWidgets.QAction(
                'New table from visible...', self)
        table_from_visible.triggered.connect(self._act_table_from_visible)
        self.tablesmenu.addAction(table_from_visible)

        # join tables
        join_tables = QtWidgets.QAction("Join tables...", self)
        join_tables.triggered.connect(self._act_join_tables)
        self.tablesmenu.addAction(join_tables)

        # remove active table
        self.tablesmenu.addSeparator()
        self.rem_cur_table = QtWidgets.QAction("Remove active table", self)
        self.rem_cur_table.triggered.connect(
                lambda: self._act_remove_table(self.active_index()))
        self.tablesmenu.addAction(self.rem_cur_table)

        # --- Show dock windows
        winmenu = menubar.addMenu("Show")
        self.dock_color = docks.ColorDockWidget(self, winmenu)
        self.dock_filters = docks.FiltersDockWidget(self, winmenu)
        self.dock_colinfo = docks.ColumnInfoDockWidget(self, winmenu)

        # --- About
        self.aboutmenu = menubar.addMenu('About')

        # =============== Load data
        self._load_database(proj)

    # =============== Actions
    def _tab_changed(self, index):
        if index >= 0:
            self._set_active_model(index)
        else:
            self._set_active_model(None)

    def _filemenu_enabled(self):
        self.export_action.setEnabled(self.active_model is not None)

    def _projectmenu_enabled(self):
        enabled = self.active_model is not None
        for m in self.projectmenu.actions():
            m.setEnabled(enabled)
        if not enabled:
            return

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

    def _tablesmenu_enabled(self):
        enabled = self.active_model is not None
        for m in self.tablesmenu.actions():
            m.setEnabled(enabled)
        if not enabled:
            return
        self.rem_cur_table.setEnabled(not self.active_model.is_original())

    def _columnsmenu_enabled(self):
        enabled = self.active_model is not None
        for m in self.columnsmenu.actions():
            m.setEnabled(enabled)
        if not enabled:
            return
        # uncollapse only if there are collapses
        self.uncollapse_cats_action.setEnabled(
            self.active_model.has_collapses())

    def _viewmenu_enabled(self):
        enabled = self.active_model is not None
        for m in self.viewmenu.actions():
            m.setEnabled(enabled)
        if not enabled:
            return

        # set checks for fold/unfold
        self.fold_rows_action.setChecked(
            self.active_model._unfolded_groups is False)
        self.unfold_rows_action.setChecked(
            self.active_model._unfolded_groups is True)

        # set checks for coloring
        self.apply_color_action.setChecked(self.active_model.use_coloring())

    def _act_open_database(self):
        flt = "Databases (*.db, *.sqlite)(*.db *.sqlite);;Any files(*)"
        filename = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open database", filter=flt)
        if filename[0]:
            self._load_database(fname=filename[0])

    def _act_zoom(self, delta):
        if self.active_model is not None:
            self.active_model.zoom_font(delta)

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
            self.active_model.update()

    def _act_group_rows(self):
        dialog = dlgs.GroupRowsDlg(
            self.active_model.dt.get_category_names(), self)
        if dialog.exec_():
            r = dialog.ret_value()
            self.active_model.group_rows(r[1], r[0])
            self.active_model.update()

    def _act_group_by_redundancy(self):
        self.active_model.group_rows(
                self.active_model.dt.get_category_names(), 'amean')
        self.active_model.update()

    def _act_ungroup_rows(self):
        self.active_model.group_rows([])
        self.active_model.update()

    def _act_collapse_all(self):
        try:
            delim = self.__last_collapse_delimiter
        except:
            delim = '-'
        if self.active_model.collapse_categories('all', True, delim):
            self.active_model.update()

    def _act_uncollapse_all(self):
        if self.active_model.remove_collapsed('all', True):
            self.active_model.update()

    def _act_collapse(self):
        dialog = dlgs.CollapseColumnsDlg(
            self.active_model.dt.get_category_names(), self)
        if dialog.exec_():
            r = dialog.ret_value()
            a = self.active_model.collapse_categories(r[2], r[0], r[1])
            if a:
                self.__last_collapse_delimiter = r[1]
                self.active_model.update()

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

    def _act_remove_table(self, i):
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
            dt = derived_tabs.JoinTable(name, tabentries, self.proj)
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
                newdt = derived_tabs.ExplicitTable(name, cols, tab, self.proj)
                self.proj.add_table(newdt)
                newmodel = tmodel.TabModel(newdt)
                index = self.add_model(newmodel)
                self.wtab.setCurrentIndex(index)

    def _act_tab_col(self):
        pass

    def _act_dictinfo(self):
        pass

    # ============== Procedures
    def _load_database(self, fname):
        if not fname:
            return
        try:
            proj = projroot.ProjectDB(fname)
            self._close_database()
            self._init_project(proj)
        except Exception as e:
            m = "Failed to load database from {}:\n".format(fname)
            qtcommon.message_exc(self, "Load error", text=m, e=e)

    def _close_database(self):
        if self.proj:
            self.proj.close_connection()
        self.proj = None
        self.models = []
        self.wtab.clear()
        self.tabframes = []

    def _init_project(self, p):
        self.proj = p
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
        if i is not None:
            self.active_model = self.models[i]
            self.active_model_changed.emit()
            self.active_model.repr_updated.connect(
                    self._forward_repr_changed)
            self.active_model.update()
        else:
            self.active_model = None
            self.active_model_changed.emit()
