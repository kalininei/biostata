from functools import partial
from PyQt5 import QtWidgets, QtGui, QtCore, QtSvg
from bgui import dlgs, optwdg, optview, qtcommon
import numpy as np
from bgui import cfg


class HClusterAct(QtWidgets.QAction):
    def __init__(self, viewwin, title,
                 icon=None, hotkey=None, checkable=False):
        super().__init__(title, viewwin)

        if icon is not None:
            self.setIcon(QtGui.QIcon(icon))

        if hotkey is not None:
            self.setShortcut(hotkey)

        self.setCheckable(checkable)

        self.triggered.connect(lambda: self.do())

        self.name = title
        self.win = viewwin
        self.scene = self.win.scene

    def isactive(self):
        return True

    def ischecked(self):
        return False

    def set_checked(self):
        if self.isEnabled() and self.isCheckable():
            self.setChecked(self.ischecked())

    def do(self):
        pass


class Refresh(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, "Sync with original table", icon=':/up-down')

    def isactive(self):
        return not self.win.is_legal_state()

    def do(self):
        self.win.calc()


class ClustersToDatabase(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Write clusters to database',
                         icon=':/writing')

    def isactive(self):
        return self.win.is_legal_state()

    def do(self):
        ngroups = self.win.spin_wdg.get_value()
        roots = self.win.linkage.get_root_groups(ngroups)
        ret = [None] * self.win.dt.n_rows()
        igroup = 0
        for r in np.nditer(roots):
            igroup += 1
            for m in np.nditer(self.win.linkage.get_group_samples(r)):
                ret[self.win.linkage.rowid[m]-1] = igroup
        # create auto name
        name = 'HC_' + self.win.opts.distance_method.split()[0]
        dlg = dlgs.GetColumnName(self.win, self.win.dt, name)
        if dlg.exec_():
            name = dlg.ret_value()
            # add new column
            self.win.add_cluster_column(name, ret)


class ExportPic(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Export picture', icon=':/save')

    def do(self):
        flist = 'PNG(*.png);;SVG(*.svg)'
        ofile = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Export graph", '', flist, 'PNG(*.png)')
        if ofile[1].startswith('SVG'):
            generator = QtSvg.QSvgGenerator()
            generator.setFileName(ofile[0])
            generator.setSize(self.scene.sceneRect().size().toSize())
            generator.setViewBox(self.scene.sceneRect())
            painter = QtGui.QPainter()
            painter.begin(generator)
            self.scene.render(painter)
            painter.end()
        else:
            image = QtGui.QImage(self.scene.sceneRect().size().toSize(),
                                 QtGui.QImage.Format_ARGB32)
            image.fill(QtCore.Qt.white)
            painter = QtGui.QPainter()
            painter.begin(image)
            self.scene.render(painter)
            painter.end()
            image.save(ofile[0])


class HClusterOptions:
    def __init__(self):
        self.distance_method = 'Ward'
        self.font_size = 10
        self.show_slider = True
        self.use_colors = True

        self.possible_distance_methods = [
            'Ward', 'Nearest Point', 'Farthest Point', 'Centroid']

    def copy_from(self, obj):
        self.distance_method = obj.distance_method
        self.show_slider = obj.show_slider
        self.use_colors = obj.use_colors
        self.font_size = obj.font_size


@qtcommon.hold_position
class SettingsDlg(dlgs.SimpleAbstractDialog):
    def __init__(self, parent, opts):
        self.iopts = opts
        super().__init__("Clustering options", parent)

    def _default_odata(self, obj):
        "-> options struct with default values"
        obj.distance_method = 'Ward'
        obj.font_size = 10
        obj.show_slider = True
        obj.use_colors = True

    def _odata_init(self):
        self.set_odata_entry('distance_method', self.iopts.distance_method)
        self.set_odata_entry('font_size', self.iopts.font_size)
        self.set_odata_entry('show_slider', self.iopts.show_slider)
        self.set_odata_entry('use_colors', self.iopts.use_colors)

    def olist(self):
        return optview.OptionsList([
            ("Method", "Distance method", optwdg.SingleChoiceOptionEntry(
                self, 'distance_method',
                self.iopts.possible_distance_methods)),
            ("Representation", "Font size", optwdg.BoundedIntOptionEntry(
                self, "font_size", 3, 100)),
            ("Representation", "Show slider", optwdg.BoolOptionEntry(
                self, "show_slider")),
            ("Representation", "Use colors", optwdg.BoolOptionEntry(
                self, "use_colors")),
            ])

    def ret_value(self):
        ret = HClusterOptions()
        ret.copy_from(self.odata())
        return ret


class Settings(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Settings', icon=':/settings')

    def do(self):
        dialog = SettingsDlg(self.win, self.win.opts)
        if dialog.exec_():
            ret = dialog.ret_value()
            need_recalc = ret.distance_method != self.win.opts.distance_method
            self.win.opts.copy_from(ret)
            if need_recalc:
                self.win.recalc()
            else:
                self.win.set_captions()
            self.scene.update()


class FitView(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Fit view', icon=":/full-size")

    def do(self):
        self.win.view.reset_size()


class MouseMove(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Mouse move', icon=":/drag")
        if not hasattr(viewwin, 'mouse_actgroup'):
            viewwin.mouse_actgroup = QtWidgets.QActionGroup(viewwin)
        viewwin.mouse_actgroup.addAction(self)
        self.setCheckable(True)

    def do(self):
        self.win.view.set_drag_mode()


class MouseZoom(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Mouse zoom', icon=":/bw-zoom")
        if not hasattr(viewwin, 'mouse_actgroup'):
            viewwin.mouse_actgroup = QtWidgets.QActionGroup(viewwin)
        viewwin.mouse_actgroup.addAction(self)
        self.setCheckable(True)

    def do(self):
        self.win.view.set_zoom_mode()


class MouseSelect(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Mouse select', icon=":/select")
        if not hasattr(viewwin, 'mouse_actgroup'):
            viewwin.mouse_actgroup = QtWidgets.QActionGroup(viewwin)
        viewwin.mouse_actgroup.addAction(self)
        self.setCheckable(True)

    def do(self):
        self.win.view.set_select_mode()


class InspectModel(QtCore.QAbstractTableModel):
    def __init__(self, linkage):
        super().__init__()
        self.linkage = linkage

    def rowCount(self, index=None):   # noqa
        return 2 + self.linkage.groups_count()

    def columnCount(self, index=None):   # noqa
        return 3 + 4 * self.linkage.source_count()

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            # captions
            if index.row() == 0:
                if index.column() == 0:
                    return 'Samples count'
                elif index.column() == 1:
                    return 'Distance'
                elif index.column() == 2:
                    return 'Mean deviation'
                else:
                    ic = int((index.column() - 3) / 4)
                    return self.linkage.colnames[ic]
            elif index.row() == 1:
                if index.column() > 2:
                    ic = (index.column() - 3) % 4
                    if ic == 0:
                        return 'mean'
                    elif ic == 1:
                        return 'std dev.'
                    elif ic == 2:
                        return 'min'
                    elif ic == 3:
                        return 'max'
            # samples count
            elif index.column() == 0:
                return np.size(self.linkage.get_group_samples(index.row() - 2))
            # distance
            elif index.column() == 1:
                return float(self.linkage.get_group_distance(index.row() - 2))
            # total standard deviation
            elif index.column() == 2:
                return float(self.linkage.group_mean_std(index.row()-2))
            else:
                colid = int((index.column() - 3)/4)
                dataid = (index.column() - 3) % 4
                if dataid == 0:
                    func = self.linkage.column_group_mean
                elif dataid == 1:
                    func = self.linkage.column_group_std
                elif dataid == 2:
                    func = self.linkage.column_group_min
                elif dataid == 3:
                    func = self.linkage.column_group_max
                return float(func(index.row() - 2, colid))
        elif role == QtCore.Qt.TextAlignmentRole:
            if index.row() < 2:
                return QtCore.Qt.AlignCenter
        elif role == QtCore.Qt.BackgroundRole:
            if index.row() < 2:
                return QtGui.QBrush(cfg.ViewConfig.get().caption_color)
        elif role == QtCore.Qt.FontRole:
            if index.row() < 2:
                return cfg.ViewConfig.get().subcaption_font()
            else:
                return cfg.ViewConfig.get().data_font()

    def headerData(self, isect, orient, role):   # noqa
        if role == QtCore.Qt.DisplayRole:
            if orient == QtCore.Qt.Vertical and isect >= 2:
                return isect - 1


class InspectColumnProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, viewwin):
        super().__init__()
        self.win = viewwin
        self.shown_columns = []
        self.shown_props = []

    def filterAcceptsRow(self, source_row, source_parent):   # noqa
        ig = source_row - 2
        if ig < 0:
            return True
        else:
            return self.win.scene.dendrogram.steps[ig].is_selected

    def filterAcceptsColumn(self, source_column, source_parent):   # noqa
        if source_column < 3:
            return True
        icol = int((source_column - 3) / 4)
        iprop = (source_column - 3) % 4
        return icol in self.shown_columns and iprop in self.shown_props


class InspectViewCols(QtWidgets.QToolButton):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, proxy, colnames):
        super().__init__(parent)
        self.setText('View columns')
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.acts = []
        for i, c in enumerate(colnames):
            act = QtWidgets.QAction(c, self)
            act.setCheckable(True)
            act.triggered.connect(partial(self._act, i))
            self.acts.append(act)
        menu = QtWidgets.QMenu(self)
        menu.addActions(self.acts)
        self.setMenu(menu)
        self.proxy = proxy

    def _act(self, icol, trig):
        if trig:
            self.proxy.shown_columns.append(icol)
        else:
            try:
                self.proxy.shown_columns.remove(icol)
            except ValueError:
                pass
        self.proxy.invalidateFilter()
        self.changed.emit()


class InspectViewProps(QtWidgets.QToolButton):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, proxy):
        super().__init__(parent)
        self.setText('View properties')
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        acts = []
        for i, c in enumerate(['mean', 'std dev.', 'min', 'max']):
            act = QtWidgets.QAction(c, self)
            act.setCheckable(True)
            act.triggered.connect(partial(self._act, i))
            acts.append(act)
        menu = QtWidgets.QMenu(self)
        menu.addActions(acts)
        self.setMenu(menu)
        self.proxy = proxy
        acts[0].trigger()

    def _act(self, iprop, trig):
        if trig:
            self.proxy.shown_props.append(iprop)
        else:
            try:
                self.proxy.shown_props.remove(iprop)
            except ValueError:
                pass
        self.proxy.invalidateFilter()
        self.changed.emit()


@qtcommon.hold_position
class InspectTable(QtWidgets.QWidget):
    def __init__(self, viewwin, linkage):
        super().__init__()
        self.setWindowIcon(viewwin.windowIcon())
        self.setWindowTitle('Selection Inspector')
        self.setLayout(QtWidgets.QVBoxLayout())
        self.tab = QtWidgets.QTableView(self)
        proxy = InspectColumnProxy(viewwin)
        proxy.setSourceModel(InspectModel(linkage))
        self.tab.setModel(proxy)

        self.toolbar = QtWidgets.QToolBar(self)
        button_viewcols = InspectViewCols(self, proxy, linkage.colnames)
        button_viewprops = InspectViewProps(self, proxy)
        act_export = QtWidgets.QAction(self)
        act_export.setIcon(QtGui.QIcon(':/excel'))
        act_export.triggered.connect(self._act_eview)
        self.toolbar.addAction(act_export)
        self.toolbar.addWidget(button_viewcols)
        self.toolbar.addWidget(button_viewprops)

        viewwin.scene.selection_changed.connect(proxy.invalidate)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.tab)
        button_viewcols.changed.connect(self.set_spans)
        button_viewprops.changed.connect(self.set_spans)
        self.set_spans()

        self.require_editor = viewwin.require_editor

    def set_spans(self):
        self.tab.clearSpans()
        self.tab.setSpan(0, 0, 2, 1)
        self.tab.setSpan(0, 1, 2, 1)
        self.tab.setSpan(0, 2, 2, 1)
        cc = len(self.tab.model().shown_props)
        if cc > 1:
            for t in range(len(self.tab.model().shown_columns)):
                self.tab.setSpan(0, 3 + cc*t, 1, cc)

    def _act_eview(self):
        from fileproc import export
        import subprocess
        try:
            # temporary filename
            fname = export.get_unused_tmp_file('xlsx')

            # # choose editor
            prog = self.require_editor('xlsx')
            if not prog:
                return
            # export to a temporary
            export.qmodel_xlsx_export(self.tab.model(), fname, vheader=True)
            # open with editor
            path = ' '.join([prog, fname])
            subprocess.Popen(path.split())
        except Exception as e:
            qtcommon.message_exc(self, "Open error", e=e)


class InspectSelection(HClusterAct):
    def __init__(self, viewwin):
        super().__init__(viewwin, 'Inspect selection', icon=":/show-tab")
        self.tabwin = None

    def do(self):
        if self.tabwin is None:
            self.tabwin = InspectTable(self.win, self.win.linkage)
        self.tabwin.show()

    def reset(self):
        if self.tabwin is not None:
            self.tabwin.close()
            del self.tabwin
        self.tabwin = None


class NClusterWidget(QtWidgets.QWidget):
    def __init__(self, viewwin):
        super().__init__(viewwin)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.spin = QtWidgets.QSpinBox(self)
        self.spin.setMinimum(1)
        self.spin.setMaximum(1)
        self.spin.valueChanged.connect(viewwin._act_set_igroup)
        self.layout().addWidget(QtWidgets.QLabel('N clusters'))
        self.layout().addWidget(self.spin)

    def get_value(self):
        return self.spin.value()

    def set_value(self, val):
        self.spin.setValue(val)

    def set_maximum(self, val):
        self.spin.setMaximum(val)


class XLabelWidget(QtWidgets.QWidget):
    def __init__(self, viewwin):
        super().__init__(viewwin)
        self.win = viewwin
        self.setLayout(QtWidgets.QHBoxLayout())
        self.combo = QtWidgets.QComboBox(self)
        self.combo.setFocusPolicy(QtCore.Qt.NoFocus)
        self.combo.currentTextChanged.connect(self._act)
        self.layout().addWidget(QtWidgets.QLabel('x-label'))
        self.layout().addWidget(self.combo)

    def set_items(self, itms):
        v = itms[:]
        if '_row index' not in itms:
            v.insert(0, '_row index')
        self.combo.clear()
        self.combo.addItems(v)

    def _act(self, txt):
        self.win.set_captions()


class SpecSelectWidget(QtWidgets.QToolButton):
    def __init__(self, viewwin):
        super().__init__(viewwin)
        self.setText('Select')
        self.win = viewwin
        self.scene = viewwin.scene
        menu = QtWidgets.QMenu(self)
        a1 = QtWidgets.QAction('None', self)
        a2 = QtWidgets.QAction('Root', self)
        a3 = QtWidgets.QAction('All', self)
        a1.triggered.connect(self._select_none)
        a2.triggered.connect(self._select_root)
        a3.triggered.connect(self._select_all)
        menu.addActions([a1, a2, a3])
        self.setMenu(menu)
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

    def _select_none(self):
        for s in self.scene.dendrogram.steps:
            s.is_selected = False
        self.scene.dendrogram.update()
        self.scene.selection_changed.emit()

    def _select_root(self):
        for s in self.scene.dendrogram.steps:
            s.is_selected = False
        ng = self.win.spin_wdg.spin.value()
        for s in self.scene.dendrogram.get_rootsteps(ng):
            s.is_selected = True
        self.scene.dendrogram.update()
        self.scene.selection_changed.emit()

    def _select_all(self):
        for s in self.scene.dendrogram.steps:
            s.is_selected = True
        self.scene.dendrogram.update()
        self.scene.selection_changed.emit()
