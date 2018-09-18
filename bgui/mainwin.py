import functools
from PyQt5 import QtWidgets, QtCore
from bgui import tmodel
from bgui import tview
from bgui import docks
from bgui import qtcommon
from bgui import mainacts
from prog import basic


class MainWindow(QtWidgets.QMainWindow):
    "application main window"
    active_model_changed = QtCore.pyqtSignal()
    active_model_repr_changed = QtCore.pyqtSignal()
    database_saved = QtCore.pyqtSignal(str)
    database_opened = QtCore.pyqtSignal(str)
    database_closed = QtCore.pyqtSignal()

    def __init__(self, proj):
        'proj - prog.projroot.ProjectDB'
        super().__init__()
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

        # assemble actions
        self._build_acts()

        # interface
        self._ui()

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

        # signals to slots
        self.active_model_repr_changed.connect(self._update_menu_status)
        self.active_model_changed.connect(self._update_menu_status)
        self.wtab.currentChanged.connect(self._tab_changed)
        self.database_saved.connect(lambda x: self._update_menu_status())
        self.database_opened.connect(lambda x: self._update_menu_status())
        self.database_closed.connect(self._update_menu_status)
        QtWidgets.qApp.aboutToQuit.connect(self._on_quit)

    def _build_acts(self):
        self.acts = {}
        for cls in mainacts.MainAct.__subclasses__():
            act = cls(self)
            self.acts[act.name] = act

    def _ui(self):
        # --------------- central widget
        self.wtab = QtWidgets.QTabWidget(self)
        self.tabframes = []
        self.setCentralWidget(self.wtab)

        # --------------- Dock widgets
        self.dock_color = docks.ColorDockWidget(self)
        self.dock_filters = docks.FiltersDockWidget(self)
        self.dock_colinfo = docks.ColumnInfoDockWidget(self)

        # --------------- Toolbar
        self._build_toolbar()

        # --------------- Menu
        self._build_menu()
        self._update_menu_status()

    def _build_menu(self):
        menubar = self.menuBar()

        # --- File
        self.filemenu = menubar.addMenu('File')
        self.filemenu.addAction(self.acts['New database'])
        self.filemenu.addAction(self.acts['Open database'])
        self.recentmenu = QtWidgets.QMenu('Open recent database')
        self.filemenu.addMenu(self.recentmenu)
        self.filemenu.addAction(self.acts['Close database'])
        self.filemenu.addAction(self.acts['Save'])
        self.filemenu.addAction(self.acts['Save as...'])
        self.filemenu.addSeparator()
        self.filemenu.addAction(self.acts['Import tables...'])
        self.filemenu.addAction(self.acts['Export tables...'])
        self.filemenu.addAction(self.acts['Open table in external viewer'])
        self.filemenu.addSeparator()
        self.filemenu.addAction(self.acts['Quit'])

        # --- View
        self.viewmenu = menubar.addMenu('View')
        self.viewmenu.addAction(self.acts['Increase font'])
        self.viewmenu.addAction(self.acts['Decrease font'])
        self.viewmenu.addSeparator()
        self.viewmenu.addAction(self.acts['Fold all groups'])
        self.viewmenu.addAction(self.acts['Unfold all groups'])
        self.viewmenu.addSeparator()
        self.viewmenu.addAction(self.acts['Apply coloring'])
        self.viewmenu.addAction(self.acts['Set coloring...'])
        self.viewmenu.addSeparator()
        self.viewmenu.addAction(self.acts['Configuration'])

        # --- Columns
        self.columnsmenu = menubar.addMenu('Columns')
        self.columnsmenu.addAction(self.acts['Collapse all categories'])
        self.columnsmenu.addAction(self.acts['Remove all collapses'])
        self.columnsmenu.addAction(self.acts['Collapse...'])

        # --- Rows
        self.rowsmenu = menubar.addMenu('Rows')
        self.rowsmenu.addAction(self.acts['Group redundancies'])
        self.groupcatmenu = QtWidgets.QMenu('Group by category')
        self.rowsmenu.addMenu(self.groupcatmenu)
        self.rowsmenu.addAction(self.acts['Group rows...'])
        self.rowsmenu.addAction(self.acts['Ungroup all'])
        self.rowsmenu.addSeparator()
        self.rowsmenu.addAction(self.acts['Add filter...'])
        self.rowsmenu.addAction(self.acts['Remove all filters'])

        # --- Tables
        self.datamenu = menubar.addMenu('Data')
        self.datamenu.addAction(self.acts["Tables && columns..."])
        self.datamenu.addAction(self.acts["Dictionaries..."])
        self.datamenu.addSeparator()
        self.datamenu.addAction(self.acts['New table from visible...'])
        self.datamenu.addAction(self.acts['Join tables...'])
        self.datamenu.addSeparator()
        self.datamenu.addAction(self.acts["Remove active table"])

        # --- Show
        self.showmenu = self.createPopupMenu()
        self.showmenu.setTitle('Show')
        menubar.addMenu(self.showmenu)

        # --- About
        self.aboutmenu = menubar.addMenu('About')

    def _build_toolbar(self):
        self.toolbar = self.addToolBar('Toolbar')
        self.toolbar.setObjectName('Toolbar')

        self.toolbar.addAction(self.acts['New database'])
        self.toolbar.addAction(self.acts['Open database'])
        self.toolbar.addAction(self.acts['Save'])
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.acts['Import tables...'])
        self.toolbar.addAction(self.acts['Export tables...'])
        self.toolbar.addAction(self.acts['Open table in external viewer'])
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.acts['Increase font'])
        self.toolbar.addAction(self.acts['Decrease font'])
        self.toolbar.addAction(self.acts['Configuration'])
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.acts['Add filter...'])
        self.toolbar.addAction(self.acts['Remove all filters'])
        self.toolbar.addAction(self.acts['Group rows...'])
        self.toolbar.addAction(self.acts['Ungroup all'])
        self.toolbar.addAction(self.acts['Fold all groups'])
        self.toolbar.addAction(self.acts['Unfold all groups'])
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.acts['New table from visible...'])
        self.toolbar.addAction(self.acts['Join tables...'])
        self.toolbar.addAction(self.acts['Remove active table'])

    # =============== Slots
    def _tab_changed(self, index):
        if index >= 0:
            self._set_active_model(index)
        else:
            self._set_active_model(None)

    def _update_menu_status(self):
        # actions
        for v in self.acts.values():
            v.setEnabled(v.isactive())

        # open recent submenu
        self.recentmenu.clear()
        if len(self.opts.recent_db) > 0:
            self.recentmenu.setEnabled(True)
            for f in self.opts.recent_db:
                act = QtWidgets.QAction(f, self)
                act.triggered.connect(functools.partial(
                    self._load_database, f))
                self.recentmenu.addAction(act)
            act = QtWidgets.QAction('Clear', self)
            act.triggered.connect(lambda: (self.opts.recent_db.clear(),
                                           self.opts.save(),
                                           self._update_menu_status()))
            self.recentmenu.addSeparator()
            self.recentmenu.addAction(act)
        else:
            self.recentmenu.setEnabled(False)

        # group categories submenus
        self.groupcatmenu.clear()
        if self.has_model():
            self.groupcatmenu.setEnabled(True)
            for c in self.active_model.dt.get_category_names():
                act = QtWidgets.QAction(c, self)
                act.triggered.connect(functools.partial(
                    self.acts['Group rows...'].group_cats, [c], 'amean'))
                self.groupcatmenu.addAction(act)
        else:
            self.groupcatmenu.setEnabled(False)

    def _on_quit(self):
        self.opts.set_mainwindow_state(self.saveState(), self.saveGeometry())
        self.opts.save()

    # ============== Procedures
    def run_act(self, aname):
        if aname in self.acts:
            self.acts[aname].do()
        else:
            raise KeyError

    def zoom_font(self, delta):
        self.opts.basic_font_size += delta
        self.reload_options(self.opts)

    def saveto(self, fname):
        try:
            self.proj.relocate_and_commit_all_changes(fname)
            self._set_actual_file(fname)
            self.database_saved.emit(fname)
        except Exception as e:
            qtcommon.message_exc(self, "Save error", e=e)
        self.update_tabnames()

    def save(self):
        try:
            self.proj.commit_all_changes()
            self.database_saved.emit(self.proj._curname)
        except Exception as e:
            qtcommon.message_exc(self, "Save error", e=e)
        self.update_tabnames()

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
            self.database_opened.emit(fname)
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
        self.database_closed.emit()

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

    def active_tview(self):
        return self.tabframes[self.active_index()]

    def add_model(self, newmodel, make_active=True):
        self.models.append(newmodel)
        self.tabframes.append(tview.TableView(newmodel, self.wtab))
        self.wtab.addTab(self.tabframes[-1], self.tabframes[-1].table_name())
        if make_active:
            self.wtab.setCurrentIndex(len(self.models) - 1)
        return len(self.models) - 1

    def _forward_repr_changed(self, a, b):
        self.active_model_repr_changed.emit()

    def _set_active_model(self, i):
        if self.active_model is not None:
            self.active_model.repr_updated.disconnect(
                    self._forward_repr_changed)
        if i is not None and i < len(self.models):
            self.active_model = self.models[i]
            self.update()
            self.active_model.repr_updated.connect(
                    self._forward_repr_changed)
        else:
            self.active_model = None
        self.active_model_changed.emit()

    def update_tabnames(self):
        for i, t in enumerate(self.models):
            cap = t.table_name()
            if t.dt.need_rewrite:
                cap += '*'
            self.wtab.setTabText(i, cap)

    def update(self):
        self.update_tabnames()
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

    def require_editor(self, ftype):
        if ftype == 'xlsx':
            ret = self.opts.external_xlsx_editor.strip()
        elif ftype == 'text':
            ret = self.opts.external_txt_editor.strip()
        else:
            raise Exception("Unknown file type: {}".format(ftype))

        if not ret:
            r = QtWidgets.QMessageBox.question(
                self, "External editor not set",
                "External {} editor was not set. "
                "Would you like to define it now?".format(ftype),
                buttons=QtWidgets.QMessageBox.Yes |
                QtWidgets.QMessageBox.No)
            if r == QtWidgets.QMessageBox.No:
                return None
            else:
                self._act_opts()
                return self.require_editor(ftype)
        return ret
