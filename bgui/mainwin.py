import functools
import traceback
from PyQt5 import QtWidgets, QtGui
from bdata import projroot
from bgui import dlgs
from bgui import tmodel
from bgui import tview
from bgui import docks
from fileproc import export


class MainWindow(QtWidgets.QMainWindow):
    "application main window"

    def __init__(self, proj=None):
        super().__init__()
        self.setWindowTitle("BioStat Analyser")
        # =========== data
        self.proj = None
        self.models = []
        self.active_model = None

        # =========== central widget
        self.wtab = QtWidgets.QTabWidget(self)
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
        # show dock windows
        self.viewmenu.addSeparator()
        winmenu = self.viewmenu.addMenu("Show")
        self.dock_color = docks.ColorDockWidget(self, winmenu)
        self.dock_filters = docks.FiltersDockWidget(self, winmenu)
        self.dock_status = docks.StatusDockWidget(self, winmenu)

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
        filter_action = QtWidgets.QAction('Filter...', self)
        filter_action.triggered.connect(self._act_filter)
        self.rowsmenu.addAction(filter_action)

        self.rem_last_filter_action = QtWidgets.QAction(
                'Cancel last filter', self)
        self.rem_last_filter_action.triggered.connect(
                lambda: (self.active_model.rem_last_filter(),
                         self.active_model.update()))
        self.rowsmenu.addAction(self.rem_last_filter_action)

        self.rem_all_filter_action = QtWidgets.QAction(
                'Cancel all filters', self)
        self.rem_all_filter_action.triggered.connect(
                lambda: (self.active_model.rem_all_filters(),
                         self.active_model.update()))
        self.rowsmenu.addAction(self.rem_all_filter_action)

        # --- About
        self.aboutmenu = menubar.addMenu('About')

        # =============== Load data
        self._load_database(proj)

    # =============== Actions
    def _filemenu_enabled(self):
        self.export_action.setEnabled(self.active_model is not None)

    def _rowsmenu_enabled(self):
        enabled = self.active_model is not None
        for m in self.rowsmenu.actions():
            m.setEnabled(enabled)
        if not enabled:
            return

        # remove filters visible
        has_flt = self.active_model.n_filters() > 0
        self.rem_last_filter_action.setEnabled(has_flt)
        self.rem_all_filter_action.setEnabled(has_flt)
        # ungroup all visible
        has_groups = self.active_model.has_groups()
        self.ungroup_rows_action.setEnabled(has_groups)

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
        dialog = dlgs.FilterRowsDlg(self.active_model.dt, self)
        if dialog.exec_():
            flts = dialog.ret_value()
            self.active_model.add_filters(flts)
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
        if self.active_model.collapse_categories('all', True):
            self.active_model.update()

    def _act_uncollapse_all(self):
        if self.active_model.remove_collapsed('all', True):
            self.active_model.update()

    def _act_collapse(self):
        dialog = dlgs.CollapseColumnsDlg(
            self.active_model.dt.get_category_names(), self)
        if dialog.exec_():
            r = dialog.ret_value()
            a = self.active_model.collapse_categories(r[2], r[0])
            if a:
                a.delimiter = r[1]
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

    # ============== Procedures
    def _load_database(self, fname):
        if not fname:
            return
        try:
            proj = projroot.ProjectDB(fname)
            self._close_database()
            self._init_project(proj)
        except Exception as e:
            print(traceback.format_exc())
            m = "Failed to load database from {}:\n{}".format(fname, e)
            QtWidgets.QMessageBox.critical(self, self.windowTitle(), m)

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
        self._init_widgets()
        self.active_model = None
        if self.models:
            self._set_active_model(0)

    def _init_widgets(self):
        self.tabframes = []
        for m in self.models:
            self.tabframes.append(tview.TableView(m, self.wtab))
        for f in self.tabframes:
            self.wtab.addTab(f, f.table_name())

    def _set_active_model(self, i):
        if self.active_model is not None:
            self.active_model.representation_changed_unsubscribe(
                self.active_model_changed)
        self.active_model = self.models[i]
        self.dock_color.active_model_changed()
        self.dock_filters.active_model_changed()
        self.dock_status.active_model_changed()
        self.active_model.representation_changed_subscribe(
            self.active_model_repr_changed)

    def active_model_repr_changed(self, model, ir):
        if self.dock_color.isVisible():
            self.dock_color.refill()
