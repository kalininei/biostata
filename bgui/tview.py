import functools
from PyQt5 import QtWidgets, QtGui, QtCore
from bdata import dtab
from bdata import bsqlproc
import resources   # noqa


class ViewConfig(object):
    _conf = None

    @classmethod
    def get(cls):
        if cls._conf is None:
            cls._conf = cls()
        return cls._conf

    def __init__(self):
        self._main_font = QtGui.QFont()
        self._main_font.setPointSize(10)
        self._margin = 3

        self.caption_color = QtGui.QColor(230, 250, 250)
        self.bg_color = QtGui.QColor(255, 255, 255)

        self.refresh()

    def refresh(self):
        self._caption_font = QtGui.QFont(self._main_font)
        self._caption_font.setBold(True)
        self._caption_font.setPointSize(self._main_font.pointSize() + 2)

        self._subcaption_font = QtGui.QFont(self._main_font)
        self._subcaption_font.setBold(True)

        self._subdata_font = QtGui.QFont(self._main_font)
        self._subdata_font.setItalic(True)
        self._subdata_font.setPointSize(self._main_font.pointSize() - 2)

        def font_height(fnt):
            return QtGui.QFontMetrics(fnt).height()
        self._data_font_height = font_height(self.data_font())
        self._subdata_font_height = font_height(self.subdata_font())
        self._caption_font_height = font_height(self.caption_font())
        self._subcaption_font_height = font_height(self.subcaption_font())

    @staticmethod
    def ftos(v):
        return format(v, '.6g')

    def data_font(self):
        return self._main_font

    def caption_font(self):
        return self._caption_font

    def subcaption_font(self):
        return self._subcaption_font

    def subdata_font(self):
        return self._subdata_font

    def data_font_height(self):
        return self._data_font_height

    def subdata_font_height(self):
        return self._subdata_font_height

    def caption_font_height(self):
        return self._caption_font_height

    def subcaption_font_height(self):
        return self._subcaption_font_height

    def margin(self):
        return self._margin


class TabDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, mod, parent):
        super().__init__(parent)
        self.view = None  # should be defined later
        self.model = mod
        self.conf = ViewConfig.get()
        self.boolpics = [QtGui.QPixmap(':/red-minus'),
                         QtGui.QPixmap(':/green-plus')]

    def _label(self, txt, font=None, fheight=None, align=None):
        w = QtWidgets.QLabel(self.view)
        if isinstance(txt, float):
            txt = self.conf.ftos(txt)
        else:
            txt = str(txt)
        w.setText(txt)
        w.setMargin(self.conf.margin())
        if font is not None:
            w.setFont(font)
        if align is not None:
            w.setAlignment(align)
        else:
            w.setAlignment(QtCore.Qt.AlignLeft)
        if fheight is not None:
            w.setMinimumSize(QtCore.QSize(0, fheight))
        return w

    def _icon_label(self, val, fheight):
        wdg = self._label('', align=QtCore.Qt.AlignCenter)
        if val:
            p = self.boolpics[0]
        else:
            p = self.boolpics[1]
        wdg.setPixmap(p.scaled(fheight, fheight))
        wdg.setMargin(self.conf.margin())
        wdg.setMinimumSize(QtCore.QSize(0, fheight))
        return wdg

    def _is_selected(self, option):
        "extract check state from QStyleOptionViewItem"
        return bool(QtWidgets.QStyle.State_Selected & option.state)

    def _vert_layout_frame(self):
        wdg = QtWidgets.QFrame()
        lab = QtWidgets.QVBoxLayout()
        lab.setContentsMargins(0, 0, 0, 0)
        lab.setSpacing(0)
        wdg.setLayout(lab)
        return lab, wdg

    def _data_widget(self, index):
        # does this row has groups?
        n_uni = self.model.dt.n_subdata_unique(index.row()-2, index.column())
        # does this row is unfolded
        is_unfolded = self.model.is_unfolded(index)
        # data to show as main
        lab, wdg = self._vert_layout_frame()
        use_icons = self.model.dt_type(index) == 'BOOLEAN'
        dt0 = index.data()
        if dt0 is None and n_uni > 1:
            dt0 = bsqlproc.group_repr(n_uni)
        if use_icons and n_uni < 2:
            a = index.data(QtCore.Qt.UserRole)
            w = self._icon_label(a, self.conf.data_font_height())
        else:
            w = self._label(dt0, self.conf.data_font(),
                            self.conf.data_font_height())
        lab.addWidget(w)
        # subdata labels
        if is_unfolded:
            lab.addStretch(1)
            if n_uni > 1:
                if use_icons:
                    sv = self.model.dt.get_raw_subvalues(
                            index.row()-2, index.column())
                else:
                    sv = self.model.dt.get_subvalues(
                            index.row()-2, index.column())
            else:
                sv = ['' for _ in range(self.model.group_size(index))]
            for v in sv:
                if v and use_icons:
                    w = self._icon_label(v, self.conf.subdata_font_height()-2)
                    w.setMargin(1)
                else:
                    w = self._label(v, self.conf.subdata_font(),
                                    self.conf.subdata_font_height())
                    w.setMargin(0)
                w.setIndent(3*self.conf.margin())
                lab.addWidget(w)
        return wdg

    def _label_widget(self, data, font, fontheight):
        lab, wdg = self._vert_layout_frame()
        w = self._label(data, font, fontheight, QtCore.Qt.AlignCenter)
        lab.addWidget(w)
        return wdg

    def _set_palette(self, wdg, cr, rr, is_selected):
        p = QtGui.QPalette(self.view.palette())
        if is_selected:
            p.setColor(QtGui.QPalette.Window,
                       p.color(QtGui.QPalette.Highlight))
            p.setColor(QtGui.QPalette.WindowText,
                       p.color(QtGui.QPalette.HighlightedText))
        elif rr != 'D' or cr == 'I':
            p.setColor(QtGui.QPalette.Window, self.conf.caption_color)
        else:
            p.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0, 0))
        wdg.setPalette(p)

    def sizeHint(self, option, index):   # noqa
        ret = super().sizeHint(option, index)
        if self.model.is_unfolded(index):
            srn = self.model.group_size(index)
        else:
            srn = 0
        h = self.conf.caption_font_height() +\
            srn * self.conf.subdata_font_height()
        ret.setHeight(h+2*self.conf.margin())
        return ret

    def paint(self, painter, option, index):   # noqa
        rr, cr = self.model.row_role(index), self.model.column_role(index)
        if rr == "D":
            # table entries widget
            wdg = self._data_widget(index)
        elif rr == "C1":
            # caption widgets
            wdg = self._label_widget(index.data(),
                                     self.conf.caption_font(),
                                     self.conf.caption_font_height())
        else:
            wdg = self._label_widget(index.data(),
                                     self.conf.subcaption_font(),
                                     self.conf.subcaption_font_height())

        # set cell color with respect to selection and role
        self._set_palette(wdg, cr, rr, self._is_selected(option))

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
        self.setFont(ViewConfig.get().data_font())
        self.delegate = TabDelegate(model, parent)
        self.delegate.view = self
        self.setItemDelegate(self.delegate)
        self.model().table_changed_subscribe(self._tab_changed)

        # header
        vh = self.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
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

    def _tab_changed(self):
        # ---------- spans
        self.clearSpans()
        # id span
        self.setSpan(0, 0, 2, 1)
        # category span
        a = self.model().n_visible_categories()
        if a > 1:
            self.setSpan(0, 1, 1, a)
        # data span
        if self.model().columnCount()-a-1 > 0:
            self.setSpan(0, a+1, 1, self.model().columnCount())
        # ---------- if cancelled ordering return v-sign to id column
        if self.model().dt.ordering is None:
            self.horizontalHeader().sortIndicatorChanged.disconnect(
                self._act_sort_column)
            self.horizontalHeader().setSortIndicator(
                    0, QtCore.Qt.AscendingOrder)
            self.horizontalHeader().sortIndicatorChanged.connect(
                self._act_sort_column)

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        if not index.isValid():
            return
        menu = QtWidgets.QMenu(self)
        rr = self.model().row_role(index)
        # fold/unfold action
        if rr == 'D' and self.model().group_size(index) > 1:
            act = QtWidgets.QAction("Fold/Unfold", self)
            act.triggered.connect(functools.partial(
                self.model().unfold_row, index, None))
            menu.addAction(act)

        # filter out the row
        if rr == 'D':
            act = QtWidgets.QAction("Filter row", self)
            act.triggered.connect(functools.partial(
                self._act_filter_row, index))
            menu.addAction(act)

        menu.popup(self.viewport().mapToGlobal(pnt))

    def _act_filter_row(self, index):
        ir = index.row()
        dc = self.model().dt.row_definition(ir-2)
        flt = dtab.FilterByValue(dc.keys(), dc.values(), True)
        self.model().add_filters([flt])
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
