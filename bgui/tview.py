import functools
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, unescape
from PyQt5 import QtWidgets, QtGui, QtCore
from prog import basic
from prog import bsqlproc
from prog import filt
from bgui import cfg
from bgui import tmodel
from bgui import maincoms
from bgui import qtcommon


def _is_selected(option):
    "extract check state from QStyleOptionViewItem"
    return bool(QtWidgets.QStyle.State_Selected & option.state)


class TabCellWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels = []
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

    def add_elabel(self, elab):
        assert isinstance(elab, qtcommon.ELabel)
        if len(self.labels) == 1:
            # to have a stretchable distance between main value and subvalues
            self.layout().addStretch(1)
        self.labels.append(elab)
        self.layout().addWidget(elab)

    def preferred_width(self):
        if len(self.labels) == 0:
            return 0
        return max([x.preferred_width() for x in self.labels])

    def preferred_height(self):
        if len(self.labels) == 0:
            return 0
        ret = sum([x.preferred_height() for x in self.labels])
        # space between main data and subdata
        if len(self.labels) > 1:
            ret += cfg.ViewConfig.get().margin()
        return ret


class TabDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, mod, parent):
        super().__init__(parent)
        self._nr, self._nc = 0, 0
        self.conf = cfg.ViewConfig.get()
        self.display_widgets = []
        self.row_heights = []
        mod.repr_updated.connect(self._representation_changed)

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
        w = qtcommon.ELabel(parent)
        w.set_elide_mode(QtCore.Qt.ElideRight)
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
        wdg = TabCellWidget()
        # group count, does this group is unfolded, number of unique
        n_tot, is_unfolded, n_uni = index.data(
                tmodel.TabModel.GroupedStatusRole)
        # main data to display
        dt0 = None
        # an icon instead of data
        use_icon = index.data(QtCore.Qt.DecorationRole)
        # if we do not need an icon
        if use_icon is None:
            dt0 = index.data(QtCore.Qt.DisplayRole)
            if dt0 is None and n_uni > 1:
                # if we do have a non-unique category group
                dt0 = bsqlproc.group_repr(n_uni)
        # use string instead of icon for bool data
        if isinstance(use_icon, str):
            dt0 = use_icon
            use_icon = None
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
        wdg.add_elabel(w)

        # subdata labels
        if is_unfolded:
            # get subdata
            dt1 = subicons = [None] * n_tot
            if n_uni > 1:
                # if non-unique group
                dt1 = index.data(tmodel.TabModel.SubDisplayRole)
                subicons = index.data(tmodel.TabModel.SubDecorationRole)
                if any([isinstance(s, str) for s in subicons]):
                    dt1 = subicons
                    subicons = [None] * n_tot
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
                wdg.add_elabel(w)
        wdg.setAutoFillBackground(True)
        self._set_palette(wdg, index)
        return wdg

    def _set_palette(self, wdg, index):
        p = QtGui.QPalette()
        fg, bg = index.data(tmodel.TabModel.ColorsRole)

        p.setColor(QtGui.QPalette.Window, bg)
        p.setColor(QtGui.QPalette.WindowText, fg)

        wdg.setPalette(p)

    def get_row_height(self, irow):
        height = self.row_heights[irow]
        if height is None:
            index = self.parent().model().createIndex(irow, 0)
            height = self._get_widget(index).preferred_height()
            self.row_heights[index.row()] = height
        return height

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

    def resizeSection(self, icol, inew):   # noqa
        inew = max(TableView._minimum_column_width, inew)
        super().resizeSection(icol, inew)


class TableView(QtWidgets.QTableView):
    _default_column_width = 70
    _minimum_column_width = 25

    def __init__(self, flow, model, parent):
        super().__init__(parent)
        self.__user_action = False
        self.flow = flow
        self.setModel(model)
        self.setItemDelegate(TabDelegate(model, self))
        self.model().repr_updated.connect(self._repr_changed)

        # header
        vh = self.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.setHorizontalHeader(HorizontalHeader(self))
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().sortIndicatorChanged.connect(
            self._act_sort_column)
        self.horizontalHeader().sectionResized.connect(
            self._section_resized)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        # column width: {column id: width}
        self.colwidth = {}
        self.__user_action = True

    def table_name(self):
        return self.model().table_name()

    def to_xml(self, root):
        ET.SubElement(root, "COLWIDTH").text = escape(str(self.colwidth))
        self.model().to_xml(root)

    def restore_from_xml(self, root):
        from ast import literal_eval
        try:
            cw = literal_eval(unescape(root.find('COLWIDTH').text))
            self.colwidth = cw
        except Exception as e:
            basic.ignore_exception(e)
        self.model().restore_from_xml(root)

    def _repr_changed(self, model=None, ir=None):
        """ model, ir arguments are used to fit model.repr_updated
            signal signature. They can be set to None safely.
        """
        self.__user_action = False
        if model is None:
            model = self.model()
        assert model is self.model()
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
        # ---------- ordering v-sign
        self.horizontalHeader().sortIndicatorChanged.disconnect(
            self._act_sort_column)
        try:
            if model.dt.ordering is None:
                a, b = 0, QtCore.Qt.AscendingOrder
            else:
                a = model.dt.column_visindex(iden=model.dt.ordering[0])
                if model.dt.ordering[1] == 'ASC':
                    b = QtCore.Qt.AscendingOrder
                else:
                    b = QtCore.Qt.DescendingOrder
            self.horizontalHeader().setSortIndicatorShown(True)
            self.horizontalHeader().setSortIndicator(a, b)
        except ValueError:
            self.horizontalHeader().setSortIndicatorShown(False)
        self.horizontalHeader().sortIndicatorChanged.connect(
            self._act_sort_column)

        # ---------- set vertical sizes
        for i in range(model.rowCount()):
            self.verticalHeader().resizeSection(i, self._get_row_height(i))

        # ---------- set horizontal sizes
        for i in range(model.columnCount()):
            self.horizontalHeader().resizeSection(i, self._get_column_width(i))
        self.__user_action = True

    def _get_row_height(self, irow):
        return self.itemDelegate().get_row_height(irow)

    def _get_column_width(self, icol):
        colid = self.model().get_column(icol).id
        try:
            return self.colwidth[colid]
        except KeyError:
            return self._default_column_width

    def _section_resized(self, icol, oldsize, newsize):
        colid = self.model().get_column(icol).id
        self.colwidth[colid] = newsize
        # add or modify a command to be able to undo it
        if self.__user_action:
            c = self.flow.last_command()
            if not isinstance(c, maincoms.ComColumnWidth) or\
                    c.aview is not self:
                c = maincoms.ComColumnWidth(self, {})
                self.flow.exec_command(c)
                c.oldw[colid] = oldsize
            c.rw[colid] = newsize

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        if not index.isValid():
            return
        menu = QtWidgets.QMenu(self)
        rr = self.model().row_role(index)

        # copy to clipboard
        if rr == 'D':
            act = QtWidgets.QAction("Copy to clipboard", self)
            act.triggered.connect(
                    functools.partial(self._act_copy_to_clipboard, index))
            menu.addAction(act)
        # fold/unfold action
        if rr == 'D' and self.model().group_size(index) > 1:
            act = QtWidgets.QAction("Fold/Unfold", self)
            act.triggered.connect(functools.partial(self._act_fold_unfold,
                                  index.row()))
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
        f = filt.filter_by_datalist(
                self.model().dt, 'id', used_ids, do_remove)
        com = maincoms.ComAddFilter(self.model(), f)
        self.flow.exec_command(com)

    def _act_sort_column(self, icol, is_desc):
        com = maincoms.ComSort(self.model(), icol, not is_desc)
        self.flow.exec_command(com)

    def _act_fold_unfold(self, irow):
        com = maincoms.ComFoldRows(self.model(), [irow], None)
        self.flow.exec_command(com)

    def _act_copy_to_clipboard(self, index=None):
        sel = self.selectionModel()
        si = sel.selectedIndexes()
        if index is not None and index not in si:
            si = si + [index]
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
            if self.model().is_unfolded(ind) and\
                    self.model().dt.n_subdata_unique(r-2, c) > 1:
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

    def selected_columns(self):
        ret = []
        si = self.selectionModel()
        for i in range(self.model().columnCount()):
            if si.columnIntersectsSelection(i, QtCore.QModelIndex()):
                ret.append(i)
        return ret

    def adjusted_width(self, how):
        """ how = 'data', 'data/caption'
        """
        ret = {}
        for i in range(self.model().columnCount()):
            cid = self.model().dt.visible_columns[i].id
            ret[cid] = self.adjusted_width_for_column(i, how)
        return ret

    def adjusted_width_for_column(self, icol, how):
        if how == 'data':
            r0 = 2
        elif how == 'data/caption':
            r0 = 1
        else:
            assert False
        deleg = self.itemDelegate()
        ind1 = deleg._linear_index(r0, icol)
        ind2 = deleg._linear_index(self.model().rowCount(), icol)
        step = self.model().columnCount()
        wmax = 0
        for j in range(ind1, ind2, step):
            w = self.itemDelegate().display_widgets[j]
            if w is None:
                continue
            wmax = max(wmax, w.preferred_width())
        wmax += self.lineWidth()
        return wmax
