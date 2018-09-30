import functools
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from bgui import qtcommon
from bgui import coloring


class MatrixModel(QtCore.QAbstractTableModel):
    def __init__(self, matrix, hheader, vheader, sym):
        super().__init__()
        self.matrix = matrix
        self.sym = sym
        self.hheader = hheader
        self.vheader = vheader
        self.cmode = 'None'
        self.minvalue = 0
        self.value_range = 1
        self.color_scheme = coloring.WhiteRed()

    def columnCount(self, index=None):   # noqa
        return np.size(self.matrix, 1)

    def rowCount(self, index=None):   # noqa
        return np.size(self.matrix, 0)

    def data(self, index, role=QtCore.Qt.DisplayRole):   # noqa
        if self.sym == 'lower' and index.row() < index.column():
            return None
        if self.sym == 'upper' and index.row() > index.column():
            return None

        if role == QtCore.Qt.DisplayRole:
            return float(self.matrix[index.row(), index.column()])
        if role == QtCore.Qt.BackgroundRole:
            if self.cmode == 'None':
                return None
            else:
                return self.get_color(self.data(index))
        return None

    def headerData(self, index, orient, role):   # noqa
        if role == QtCore.Qt.DisplayRole:
            if orient == QtCore.Qt.Vertical and self.vheader is not None:
                return self.vheader[index]
            if orient == QtCore.Qt.Horizontal and self.hheader is not None:
                return self.hheader[index]

    def get_color(self, val):
        if self.cmode == 'Absolute value':
            val = abs(val)
        val = (val - self.minvalue)/self.value_range
        return self.color_scheme.get_color(val)

    def set_color_mode(self, mode):
        self.beginResetModel()
        self.cmode = mode
        if self.cmode == 'Absolute value':
            a = np.absolute(self.matrix)
        elif self.cmode == 'Value':
            a = self.matrix
        else:
            a = np.array([0])
        self.minvalue = np.min(a)
        self.value_range = np.max(a) - self.minvalue
        if self.value_range == 0:
            self.value_range = 1
        self.endResetModel()


class MatrixTabView(QtWidgets.QTableView):
    def __init__(self, parent):
        super().__init__(parent)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        if not index.isValid():
            return
        menu = QtWidgets.QMenu(self)
        # copy to clipboard
        act = QtWidgets.QAction("Copy to clipboard", self)
        act.triggered.connect(
                functools.partial(self._act_copy_to_clipboard, index))
        menu.addAction(act)
        menu.popup(self.viewport().mapToGlobal(pnt))

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
            v = self.model().data(self.model().createIndex(r, c))
            if v is None:
                v = ""
            tab[r-minr][c-minc] = v
        # convert into text and place to the clipboard
        txt = []
        for row in tab:
            txt.append('\t'.join(map(str, row)))
        txt = '\n'.join(txt)
        QtWidgets.QApplication.clipboard().setText(txt)


@qtcommon.hold_position
class MatrixView(QtWidgets.QWidget):
    def __init__(self, title, mainwin, matrix,
                 hheader=None, vheader=None, sym="both"):
        super().__init__()
        self.mw = mainwin
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setWindowIcon(mainwin.windowIcon())
        self.setWindowTitle(title)
        self.tab = MatrixTabView(self)
        self.tab.setModel(MatrixModel(matrix, hheader, vheader, sym))
        # menu frame
        self.mframe = QtWidgets.QFrame(self)
        self.mframe.setLayout(QtWidgets.QHBoxLayout())
        self.mframe.layout().addStretch(1)
        self.eview_button = QtWidgets.QToolButton(self)
        self.eview_button.setIcon(QtGui.QIcon(':/excel'))
        self.eview_button.clicked.connect(self._act_eview)
        self.mframe.layout().addWidget(self.eview_button)
        self.mframe.layout().addWidget(QtWidgets.QLabel('Color by'))
        self.color_cb = QtWidgets.QComboBox(self)
        self.color_cb.addItems(['None', 'Value', 'Absolute value'])
        self.color_cb.currentTextChanged.connect(self._act_color)
        self.mframe.layout().addWidget(self.color_cb)
        self.layout().addWidget(self.mframe)
        # place table
        self.layout().addWidget(self.tab)

    def _act_eview(self):
        from fileproc import export
        import subprocess
        try:
            # temporary filename
            fname = export.get_unused_tmp_file('xlsx')

            # choose editor
            prog = self.mw.require_editor('xlsx')
            if not prog:
                return
            # export to a temporary
            export.qmodel_xlsx_export(self.tab.model(), fname, True, True)
            # open with editor
            path = ' '.join([prog, fname])
            subprocess.Popen(path.split())
        except Exception as e:
            qtcommon.message_exc(self, "Open error", e=e)

    def _act_color(self, c):
        self.tab.model().set_color_mode(c)
