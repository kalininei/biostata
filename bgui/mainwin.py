import functools
import xml.etree.ElementTree as ET
from PyQt5 import QtWidgets, QtCore, QtGui
from bgui import tmodel
from bgui import tview
from bgui import docks
from bgui import qtcommon
from bgui import mainacts
from prog import basic
import prog


class MainWindow(QtWidgets.QMainWindow):
    "application main window"
    active_model_changed = QtCore.pyqtSignal()
    active_model_repr_changed = QtCore.pyqtSignal()
    database_saved = QtCore.pyqtSignal()
    database_opened = QtCore.pyqtSignal()
    database_closed = QtCore.pyqtSignal()

    def __init__(self, flow, proj, opts):
        'proj - prog.projroot.ProjectDB'
        super().__init__()
        # init position (will be changed by opts data)
        self.resize(800, 600)
        self.setWindowIcon(QtGui.QIcon(":/biostata"))
        self.setGeometry(QtWidgets.QStyle.alignedRect(
            QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
            self.size(), QtWidgets.qApp.desktop().availableGeometry()))
        self.__subwindows = []

        # data
        self.proj = proj
        self.flow = flow
        self.opts = opts

        self.models = []
        self.tabframes = []
        self.active_model = None
        self.reload_options()

        # assemble actions
        self._build_acts()

        # interface
        self._ui()

        # restore
        try:
            state, geom = self.opts.mainwindow_state()
            self.restoreState(state)
            self.restoreGeometry(geom)
        except Exception as e:
            basic.ignore_exception(e)

        # signals to slots
        self.flow.command_done.add_subscriber(self._update_menu_status)
        self.active_model_changed.connect(self._update_menu_status)
        self.database_saved.connect(self._update_menu_status)
        self.wtab.currentChanged.connect(self._tab_changed)
        self.proj.xml_saved.add_subscriber(self.to_xml)
        self.proj.xml_loaded.add_subscriber(self.restore_from_xml)
        self.proj.monitor_recent_db(self.opts)
        QtWidgets.qApp.aboutToQuit.connect(self._on_quit)

        # Load data
        self.reset_title()
        filename = self.opts.default_project_filename()
        if filename is not None:
            try:
                self.acts['Open database'].load(filename)
            except Exception as e:
                qtcommon.message_exc(self, "Load error", e=e)
                self._close_database()

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

        # --- Edit
        self.editmenu = menubar.addMenu('Edit')
        self.editmenu.addAction(self.acts['Undo'])
        self.editmenu.addAction(self.acts['Redo'])

        # --- View
        self.viewmenu = menubar.addMenu('View')
        self.viewmenu.addAction(self.acts['Increase font'])
        self.viewmenu.addAction(self.acts['Decrease font'])
        self.setwidthmenu = QtWidgets.QMenu("Set columns width")
        self.setwidthmenu.addAction(self.acts['Fit to data width'])
        self.setwidthmenu.addAction(self.acts['Fit to data and caption width'])
        self.setwidthmenu.addAction(self.acts['Set constant width...'])
        self.viewmenu.addMenu(self.setwidthmenu)
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
        self.columnsmenu.addSeparator()
        self.columnsmenu.addAction(self.acts['Numerical function...'])
        self.aggrmenu = QtWidgets.QMenu('Aggregate function')
        self.aggrmenu.addAction(self.acts['Integral...'])
        self.aggrmenu.addAction(self.acts['Regression...'])
        self.columnsmenu.addMenu(self.aggrmenu)

        # --- Rows
        self.rowsmenu = menubar.addMenu('Rows')
        self.rowsmenu.addAction(self.acts['Group all'])
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

        # --- Stats
        self.statsmenu = menubar.addMenu('Stats')
        self.statsmenu.addAction(self.acts['Covariance matrix'])
        self.statsmenu.addAction(self.acts['Correlation matrix'])

        # --- Show
        self.showmenu = self.createPopupMenu()
        self.showmenu.setTitle('Show')
        menubar.addMenu(self.showmenu)

        # --- About
        self.aboutmenu = menubar.addMenu('About')
        aboutbiostata = QtWidgets.QAction('About BioStatA', self)
        aboutbiostata.triggered.connect(functools.partial(
            QtWidgets.QMessageBox.about,
            self,
            'BioStat Analyser',
            '<b>BioStat Analyser</b> <br><br>'
            'Version {0} <br><br>'
            '<a href="http://{1}/releases/latest">{1}</a>'
            ''.format(prog.version, "www.github.com/kalininei/biostata/")))
        self.aboutmenu.addAction(aboutbiostata)
        aboutqt = QtWidgets.QAction('About Qt', self)
        aboutqt.triggered.connect(QtWidgets.QApplication.aboutQt)
        self.aboutmenu.addAction(aboutqt)

    def _build_toolbar(self):
        self.toolbar = self.addToolBar('Toolbar')
        self.toolbar.setObjectName('Toolbar')

        self.toolbar.addAction(self.acts['New database'])
        self.toolbar.addAction(self.acts['Open database'])
        self.toolbar.addAction(self.acts['Save'])
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.acts['Undo'])
        self.toolbar.addAction(self.acts['Redo'])
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.acts['Import tables...'])
        self.toolbar.addAction(self.acts['Export tables...'])
        self.toolbar.addAction(self.acts['Open table in external viewer'])
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.acts['Increase font'])
        self.toolbar.addAction(self.acts['Decrease font'])
        self.toolbar.addAction(self.acts['Fit to data width'])
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
        # this is called after each command, so we place some checks here
        # assert self.wtab.count() == len(self.tabframes),\
        # ############################################################
        # if self.wtab.count() != len(self.tabframes):
        #     print("{} != {}".format(self.wtab.count(), len(self.tabframes)))
        #     import traceback
        #     traceback.print_stack()
        # for mod in self.models:
        #     for col in mod.dt.all_columns:
        #         if not col.uses_dict(None):
        #             did = col.repr_delegate.dict.id
        #             did = self.proj.get_dictionary(iden=did)
        #             assert did is col.repr_delegate.dict

        # actions
        for v in self.acts.values():
            v.setEnabled(v.isactive())

        # checked
        self.acts['Apply coloring'].set_checked()

        # open recent submenu
        self.recentmenu.clear()
        if len(self.opts.recent_db) > 0:
            self.recentmenu.setEnabled(True)
            for f in self.opts.recent_db:
                act = QtWidgets.QAction(f, self)
                act.triggered.connect(functools.partial(
                    self.acts['Open database'].load, f))
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

    def closeEvent(self, event):   # noqa
        for w in self.__subwindows[:]:
            w.close()
        event.accept()

    # ============== Procedures
    def run_act(self, aname):
        if aname in self.acts:
            self.acts[aname].do()
        else:
            raise KeyError

    def zoom_font(self, delta):
        self.opts.basic_font_size += delta
        self.reload_options()

    def save(self):
        try:
            self.proj.commit_all_changes()
            self.database_saved.emit()
        except Exception as e:
            qtcommon.message_exc(self, "Save error", e=e)

    def to_xml(self, nd):
        root = ET.SubElement(nd, "PROGVIEW")
        if len(self.models) == 0:
            return
        ET.SubElement(root, "CURRENT_TAB").text = str(self.active_index())
        for t in self.tabframes:
            a = ET.SubElement(root, "TAB")
            ET.SubElement(a, "NAME").text = t.table_name()
            t.to_xml(a)

    def restore_from_xml(self, nd):
        self._close_database()
        self._init_project()
        root = nd.find('PROGVIEW')
        if root is None:
            return
        for f in root.findall('TAB'):
            nm = f.find('NAME').text
            for t in self.tabframes:
                if t.table_name() == nm:
                    t.restore_from_xml(f)
                    break
            else:
                assert False, '{}'.format(nm)
        try:
            ct = int(root.find('CURRENT_TAB').text)
            self.wtab.setCurrentIndex(ct)
        except Exception as e:
            basic.ignore_exception(e)

    def reset_title(self):
        self.setWindowTitle(self.proj._curname + " - BioStat Analyser")

    def _close_database(self):
        self.active_model = None
        self.models.clear()
        self.tabframes.clear()
        self.wtab.clear()
        self.reset_title()
        self.database_closed.emit()

    def _init_project(self):
        self.models.clear()
        # models
        for t in self.proj.data_tables:
            self.models.append(tmodel.TabModel(t))
        if self.models:
            self.active_model = self._set_active_model(0)
        self._init_widgets()

    def _init_widgets(self):
        self.tabframes.clear()
        for m in self.models:
            self.tabframes.append(tview.TableView(self.flow, m, self.wtab))
        for f in self.tabframes:
            self.wtab.addTab(f, f.table_name())

    def has_model(self):
        return self.active_model is not None

    def active_index(self):
        return self.models.index(self.active_model)

    def active_tview(self):
        return self.tabframes[self.active_index()]

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

    def update(self):
        if self.active_model:
            self.active_model.update()

    def view_update(self):
        if self.active_model:
            self.active_model.view_update()

    def reload_options(self):
        from bgui import cfg

        cfg.ViewConfig.set_real_precision(self.opts.real_numbers_prec)
        cfg.ViewConfig.get()._basic_font_size = self.opts.basic_font_size
        cfg.ViewConfig.get()._show_bool =\
            {'icons': cfg.ViewConfig.BOOL_AS_ICONS,
             'codes': cfg.ViewConfig.BOOL_AS_CODES,
             'Yes/No': cfg.ViewConfig.BOOL_AS_YESNO}[self.opts.show_bool_as]
        cfg.ViewConfig.get().refresh()
        self.opts.basic_font_size = cfg.ViewConfig.get()._basic_font_size
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
                self.run_act('Configuration')
                return self.require_editor(ftype)
        return ret

    def add_subwindow(self, win):
        self.__subwindows.append(win)
        win.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        win.destroyed.connect(lambda: self.__subwindows.remove(win))
