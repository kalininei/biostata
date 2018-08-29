import functools
from PyQt5 import QtWidgets, QtGui, QtCore
from bdata import bsqlproc
from bdata import filt
from bgui import cfg
from bgui import tmodel


def _is_selected(option):
    "extract check state from QStyleOptionViewItem"
    return bool(QtWidgets.QStyle.State_Selected & option.state)


def _vert_layout_frame():
    wdg = QtWidgets.QFrame()
    lab = QtWidgets.QVBoxLayout()
    lab.setContentsMargins(0, 0, 0, 0)
    lab.setSpacing(0)
    wdg.setLayout(lab)
    return wdg


class TabDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, mod, parent):
        super().__init__(parent)
        self.conf = cfg.ViewConfig.get()
        self.display_widgets = []
        self.row_heights = []
        mod.representation_changed_subscribe(self._representation_changed)

    def _representation_changed(self, model, ir):
        """ fired from model if smth changed in representation of ir-th row
        """
        self._nr, self._nc = model.rowCount(), model.columnCount()
        if ir == -1:
            self.display_widgets = [None] * (self._nr * self._nc)
            self.row_heights = [None] * self._nr
        else:
            for i in range(self._linear_index(ir, 0),
                           self._linear_index(ir+1, 0)):
                self.display_widgets[i] = None
            self.row_heights[ir] = None

    def _linear_index(self, ir, ic):
        return ir * self._nc + ic

    def _label(self, txt, parent):
        w = QtWidgets.QLabel(parent)
        if txt is not None:
            if isinstance(txt, float):
                w.setText(self.conf.ftos(txt))
            else:
                w.setText(str(txt))
        return w

    def _get_widget(self, index):
        """ checks if widgets is already created, create it if needed
            and return
        """
        li = self._linear_index(index.row(), index.column())
        if self.display_widgets[li] is None:
            w = self._build_widget(index)
            self.display_widgets[li] = w
        return self.display_widgets[li]

    def _build_widget(self, index):
        """ builds a widget, fills it with data, font, palette
            and minimum height
        """
        # create widget frame
        wdg = _vert_layout_frame()
        self._set_palette(wdg, index)
        # group count, does this group is unfolded, number of unique
        n_tot, is_unfolded, n_uni = index.data(
                tmodel.TabModel.GroupedStatusRole)
        # an icon instead of data
        use_icon = index.data(QtCore.Qt.DecorationRole)
        # main data to display
        dt0 = None
        # if we do not need an icon
        if use_icon is None:
            dt0 = index.data(QtCore.Qt.DisplayRole)
            if dt0 is None and n_uni > 1:
                # if we do have a non-unique category group
                dt0 = bsqlproc.group_repr(n_uni)
        # add main value data
        w = self._label(dt0, wdg)
        w.setFont(index.data(QtCore.Qt.FontRole))
        if use_icon:
            w.setPixmap(use_icon)
            w.setAlignment(QtCore.Qt.AlignCenter)
        else:
            w.setAlignment(QtCore.Qt.Alignment(
                index.data(QtCore.Qt.TextAlignmentRole)))
        w.setMargin(self.conf.margin())
        wdg.layout().addWidget(w)

        # subdata labels
        if is_unfolded:
            # to have a stretchable distance between main value and subvalues
            wdg.layout().addStretch(1)
            # get subdata
            dt1 = subicons = [None] * n_tot
            if n_uni > 1:
                # if non-unique group
                dt1 = index.data(tmodel.TabModel.SubDisplayRole)
                subicons = index.data(tmodel.TabModel.SubDecorationRole)
            # request font for subdata
            fnt = index.data(tmodel.TabModel.SubFontRole)
            # construct sublabels
            for d, ic in zip(dt1, subicons):
                w = self._label(d, wdg)
                w.setFont(fnt)
                w.setIndent(3 * self.conf.margin())
                if n_uni > 1 and ic is not None:
                    w.setPixmap(ic)
                    w.setAlignment(QtCore.Qt.AlignCenter)
                else:
                    w.setAlignment(QtCore.Qt.AlignLeft)
                wdg.layout().addWidget(w)
        wdg.setAutoFillBackground(True)
        return wdg

    def _set_palette(self, wdg, index):
        p = QtGui.QPalette()
        fg, bg = index.data(tmodel.TabModel.ColorsRole)

        p.setColor(QtGui.QPalette.Window, bg)
        p.setColor(QtGui.QPalette.WindowText, fg)

        wdg.setPalette(p)

    def sizeHint(self, option, index):   # noqa
        if self.row_heights[index.row()] is None:
            f1 = index.data(QtCore.Qt.FontRole)
            # main data font
            height = QtGui.QFontMetrics(f1).height()
            # margins for main data
            height += 2 * self.conf.margin()
            n, unfolded, _ = index.data(tmodel.TabModel.GroupedStatusRole)
            if unfolded:
                f2 = index.data(tmodel.TabModel.SubFontRole)
                # subrows data font
                height += n * QtGui.QFontMetrics(f2).height()
            # space between main data and subdata
            if unfolded:
                height += self.conf.margin()
            self.row_heights[index.row()] = QtCore.QSize(-1, height)

        return self.row_heights[index.row()]

    def paint(self, painter, option, index):   # noqa
        wdg = self._get_widget(index)

        # switch to selected role if needed
        if _is_selected(option):
            wdg.setBackgroundRole(QtGui.QPalette.Highlight)
            wdg.setForegroundRole(QtGui.QPalette.HighlightedText)
        else:
            wdg.setBackgroundRole(QtGui.QPalette.Window)
            wdg.setForegroundRole(QtGui.QPalette.WindowText)

        # paint widget
        painter.save()

        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.translate(option.rect.topLeft())
        wdg.resize(option.rect.size())
        wdg.render(painter)

        painter.restore()


class HorizontalHeader(QtWidgets.QHeaderView):
    def __init__(self, parent):
        super().__init__(QtCore.Qt.Horizontal, parent)
        self.setSortIndicator(0, QtCore.Qt.AscendingOrder)
        # disable clicks to forbid automatic sorting because
        # we want to use right mouse button for sorting
        # and left button for column selection
        self.setSectionsClickable(False)

    def mousePressEvent(self, event):   # noqa
        if event.button() == QtCore.Qt.RightButton:
            col = self.logicalIndexAt(event.pos())
            order = QtCore.Qt.AscendingOrder
            oldcol = self.sortIndicatorSection()
            oldorder = self.sortIndicatorOrder()
            if col == oldcol and oldorder == QtCore.Qt.AscendingOrder:
                order = QtCore.Qt.DescendingOrder
            self.setSortIndicator(col, order)

        # enable clicks temporary to enable column selections
        self.setSectionsClickable(True)
        super().mousePressEvent(event)
        self.setSectionsClickable(False)

    def mouseMoveEvent(self, event):   # noqa
        self.setSectionsClickable(True)
        super().mouseMoveEvent(event)
        self.setSectionsClickable(False)


class TableView(QtWidgets.QTableView):
    def __init__(self, model, parent):
        super().__init__(parent)
        self.setModel(model)
        self.setItemDelegate(TabDelegate(model, parent))
        self.model().representation_changed_subscribe(self._repr_changed)

        # header
        vh = self.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.setHorizontalHeader(HorizontalHeader(self))
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().sortIndicatorChanged.connect(
            self._act_sort_column)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        # here we fill model with original data
        self.model().update()

    def table_name(self):
        return self.model().table_name()

    def _repr_changed(self, model, ir):
        # ---------- spans
        self.clearSpans()
        # id span
        self.setSpan(0, 0, 2, 1)
        # category span
        a = model.n_visible_categories()
        if a > 1:
            self.setSpan(0, 1, 1, a)
        # data span
        if model.columnCount()-a-1 > 0:
            self.setSpan(0, a+1, 1, model.columnCount())
        # ---------- if cancelled ordering return v-sign to id column
        if model.dt.ordering is None:
            self.horizontalHeader().sortIndicatorChanged.disconnect(
                self._act_sort_column)
            self.horizontalHeader().setSortIndicator(
                    0, QtCore.Qt.AscendingOrder)
            self.horizontalHeader().sortIndicatorChanged.connect(
                self._act_sort_column)

        # ---------- set vertical sizes
        for i in range(model.rowCount()):
            index = model.createIndex(i, 0)
            h = self.itemDelegate().sizeHint(None, index).height()
            self.verticalHeader().resizeSection(i, h)

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        if not index.isValid():
            return
        menu = QtWidgets.QMenu(self)
        rr = self.model().row_role(index)

        # copy to clipboard
        if rr == 'D':
            act = QtWidgets.QAction("Copy", self)
            act.triggered.connect(self._act_copy_to_clipboard)
            menu.addAction(act)
        # fold/unfold action
        if rr == 'D' and self.model().group_size(index) > 1:
            act = QtWidgets.QAction("Fold/Unfold", self)
            act.triggered.connect(functools.partial(
                self.model().unfold_row, index, None))
            menu.addAction(act)

        # filter out the row
        if rr == 'D':
            act = QtWidgets.QAction("Filter rows", self)
            act.triggered.connect(functools.partial(
                self._act_filter_row, index, True))
            menu.addAction(act)
            act = QtWidgets.QAction("Leave only rows", self)
            act.triggered.connect(functools.partial(
                self._act_filter_row, index, False))
            menu.addAction(act)

        menu.popup(self.viewport().mapToGlobal(pnt))

    def _act_filter_row(self, index, do_remove):
        sel = self.selectionModel()
        usedrows = set([index.row()])
        for si in sel.selectedIndexes():
            usedrows.add(si.row())
        used_ids = []
        for ir in usedrows:
            a = self.model().dt.ids_by_row(ir-2)
            used_ids.extend(a)
        f = filt.Filter.filter_by_datalist(
                self.model().dt, 'id', used_ids, do_remove)
        self.model().add_filter(f)
        # preserve fold/unfold set which will be altered after update()
        bu = None
        if not isinstance(self.model()._unfolded_groups, bool):
            bu = set()
            for r in self.model()._unfolded_groups:
                if r < ir:
                    bu.add(r)
                elif r > ir:
                    bu.add(r-1)

        self.model().update()
        if bu is not None:
            self.model()._unfolded_groups = bu
            self.model().modelReset.emit()

    def _act_sort_column(self, icol, is_desc):
        # preserve fold/unfold set which will be altered after update()
        bu = None
        if not isinstance(self.model()._unfolded_groups, bool):
            bu = set()
            for r in self.model()._unfolded_groups:
                bu.add(self.model().row_min_id(r))

        # sorting
        self.model().set_sorting(self.model().column_name(icol), not is_desc)
        self.model().update()

        # restore fold/unfold. After the update() _unfolded_groups is boolean
        if bu is not None:
            for i in range(self.model().rowCount()):
                if self.model().row_min_id(i) in bu:
                    index = self.model().createIndex(i, 0)
                    self.model().unfold_row(index, True)

    def _act_copy_to_clipboard(self):
        sel = self.selectionModel()
        si = sel.selectedIndexes()
        maxr = max([x.row() for x in si])
        minr = min([x.row() for x in si])
        maxc = max([x.column() for x in si])
        minc = min([x.column() for x in si])
        nx = maxc - minc + 1
        ny = maxr - minr + 1
        tab = [[""]*nx for _ in range(ny)]
        # fill tab
        for ind in si:
            r, c = ind.row(), ind.column()
            v = self.model().dt.get_value(r-2, c)
            if v is None:
                v = ""
            if self.model().dt.n_subdata_unique(r-2, c) > 1:
                sv = self.model().dt.get_subvalues(r-2, c)
                sv = ", ".join(map(str, sv))
                v = "{}({})".format(v, sv)
            tab[r-minr][c-minc] = v
        # convert into text and place to the clipboard
        txt = []
        for row in tab:
            txt.append('\t'.join(map(str, row)))
        txt = '\n'.join(txt)
        QtWidgets.QApplication.clipboard().setText(txt)
