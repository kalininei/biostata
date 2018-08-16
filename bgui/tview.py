import functools
from PyQt5 import QtWidgets, QtGui, QtCore
from bdata import dtab


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

    def _label(self, txt, font=None, fheight=None, align=None):
        if isinstance(txt, float):
            txt = self.conf.ftos(txt)
        else:
            txt = str(txt)
        w = QtWidgets.QLabel(txt, self.view)
        w.setMargin(self.conf.margin())
        if font is not None:
            w.setFont(font)
        if align is not None:
            w.setAlignment(align)
        else:
            w.setAlignment(QtCore.Qt.AlignLeft)
        if fheight is not None:
            w.setMaximumSize(QtCore.QSize(
                16777215, fheight + 2*self.conf.margin()))
        return w

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
        dt0 = index.data()
        if dt0 is None and n_uni > 1:
            dt0 = '...[' + str(n_uni) + ']'
        # main label
        lab, wdg = self._vert_layout_frame()
        w = self._label(dt0, self.conf.data_font(),
                        self.conf.data_font_height())
        lab.addWidget(w)
        # subdata labels
        if is_unfolded:
            lab.addStretch(1)
            if n_uni > 1:
                sv = self.model.dt.get_subvalues(index.row()-2, index.column())
            else:
                sv = ['' for _ in range(self.model.group_size(index))]
            for v in sv:
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


class TableView(QtWidgets.QTableView):
    def __init__(self, model, parent):
        super().__init__(parent)
        self.setModel(model)
        self.setFont(ViewConfig.get().data_font())
        self.delegate = TabDelegate(model, parent)
        self.delegate.view = self
        self.setItemDelegate(self.delegate)
        self.model().table_changed_subscribe(self._set_cells_span)

        # header
        vh = self.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        # here we fill model with original data
        self.model().update()

    def table_name(self):
        return self.model().table_name()

    def _set_cells_span(self):
        # id span
        self.setSpan(0, 0, 2, 1)
        # category span
        a = self.model().n_categories()
        self.setSpan(0, 1, 1, a)
        # data span
        self.setSpan(0, a+1, 1, self.model().columnCount())

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
