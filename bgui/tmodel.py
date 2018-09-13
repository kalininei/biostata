import copy
from PyQt5 import QtCore, QtGui
from bgui import coloring
from bgui import cfg


class TabModel(QtCore.QAbstractTableModel):
    """ This class contains representation options
        for resulting table (presented as bdata.dtab.DataTable self.dt)
        including color, folds etc.
        It also connects directly to a View object and works as
        a controller.
    """
    repr_updated = QtCore.pyqtSignal('PyQt_PyObject', int)
    # additional roles for data(...) execution
    RawValueRole = QtCore.Qt.UserRole
    RawSubValuesRole = QtCore.Qt.UserRole+1
    GroupedStatusRole = QtCore.Qt.UserRole+2
    ColorsRole = QtCore.Qt.UserRole+3
    SubFontRole = QtCore.Qt.UserRole+4
    SubDisplayRole = QtCore.Qt.UserRole+5
    SubDecorationRole = QtCore.Qt.UserRole+6

    def __init__(self, dt):
        super().__init__()
        self.conf = cfg.ViewConfig.get()
        self.dt = dt
        # False -- all are folded, True -- all are unfolded,
        # set() indicies of unfolded rows, which vanish at update()
        self._unfolded_groups = False
        # color scheme
        self.coloring = coloring.Coloring(self.dt)
        self.repr_updated.connect(
                lambda t, i: self.coloring.update(t.dt) if i == -1 else None)

    # overwritten methods
    def rowCount(self, parent=None):    # noqa
        return self.dt.n_rows() + 2

    def columnCount(self, parent=None):   # noqa
        return self.dt.n_cols()

    def flags(self, index):   # noqa
        ret = QtCore.Qt.ItemIsEnabled
        if index.row() >= 2:
            ret = ret | QtCore.Qt.ItemIsSelectable
        return ret

    def headerData(self, ind, orient, role):   # noqa
        if role == QtCore.Qt.DisplayRole:
            if orient == QtCore.Qt.Horizontal:
                return ind+1
            else:
                return ind-1 if ind > 1 else None
        return super().headerData(ind, orient, role)

    def data(self, index, role):   # noqa
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        rr, cr = self.row_role(index), self.column_role(index)

        # --- displayed values
        if role == QtCore.Qt.DisplayRole:
            if rr == 'C1':
                if cr == 'I':
                    return "Id"
                elif cr == 'C':
                    return "Categorical"
                else:
                    return "Real"
            elif rr == 'C2':
                return self.dt.column_caption(index.column())
            else:
                return self.dt.get_value(index.row()-2, index.column())
        # --- colors: foreground, background
        elif role == self.ColorsRole:
            fg = QtGui.QPalette().color(QtGui.QPalette.WindowText)
            if rr[0] == 'C' or cr == 'I':
                bg = self.conf.caption_color
            else:
                bg = self.coloring.get_color(r-2)
                if bg is None:
                    bg = self.conf.bg_color
                else:
                    fg = coloring.get_foreground(bg)
            return fg, bg
        # --- Status of the group: (group size, is unfolded, unique size)
        elif role == self.GroupedStatusRole:
            if r < 2 or not self.has_groups():
                return (0, False, 0)
            else:
                return (self.dt.n_subrows(r-2),
                        self.is_unfolded(index),
                        self.dt.n_subdata_unique(r-2, c))
        # --- Show an icon instead of data
        elif role == QtCore.Qt.DecorationRole:
            if r > 1 and self.dt.visible_columns[c].dt_type == 'BOOL':
                v = self.data(index, self.RawValueRole)
                if v == 1:
                    return self.conf.true_icon(self.use_coloring())
                elif v == 0:
                    return self.conf.false_icon(self.use_coloring())
            return None
        # --- font
        elif role == QtCore.Qt.FontRole:
            if rr == 'C1':
                return self.conf.caption_font()
            elif rr == 'C2':
                return self.conf.subcaption_font()
            else:
                return self.conf.data_font()
        # --- text alignment
        elif role == QtCore.Qt.TextAlignmentRole:
            if rr[0] == 'C':
                return QtCore.Qt.AlignCenter
            else:
                return QtCore.Qt.AlignLeft
        # --- raw values
        elif role == self.RawValueRole:
            if r > 1:
                return self.dt.get_raw_value(r-2, c)
            else:
                return self.data(index, QtCore.QtDisplayRole)
        # --- raw subvalues
        elif role == self.RawSubValuesRole:
            if r > 1:
                return self.dt.get_raw_subvalues(r-2, c)
            else:
                return None
        # --- font of subdata
        elif role == self.SubFontRole:
            return self.conf.subdata_font()
        # --- subrows values
        elif role == self.SubDisplayRole:
            return self.dt.get_subvalues(r-2, c)
        # --- subrows icons
        elif role == self.SubDecorationRole:
            ret = [None]*self.dt.n_subrows(r-2)
            if r > 1 and self.dt.visible_columns[c].dt_type == 'BOOL':
                v = index.data(self.RawSubValuesRole)
                for i, a in enumerate(v):
                    if a == 1:
                        ret[i] = self.conf.true_subicon(self.use_coloring())
                    elif a == 0:
                        ret[i] = self.conf.false_subicon(self.use_coloring())
            return ret
        else:
            if role not in [3, 4]:
                raise NotImplementedError

        return None

    def update(self):
        """ make a new query and recalculate the table """
        self.beginResetModel()
        self.dt.update()
        if not isinstance(self._unfolded_groups, bool):
            self._unfolded_groups = False
        self.endResetModel()
        self.repr_updated.emit(self, -1)

    def view_update(self):
        self.modelReset.emit()
        self.repr_updated.emit(self, -1)

    # ------------------------ information procedures
    def table_name(self):
        return self.dt.table_name()

    def is_original(self):
        return self.dt.is_original()

    def group_size(self, index):
        ir = index.row()
        if ir < 2:
            return 0
        else:
            return self.dt.n_subrows(ir-2)

    def is_unfolded(self, index):
        if self.group_size(index) < 2:
            return False
        if isinstance(self._unfolded_groups, bool):
            return self._unfolded_groups
        else:
            return index.row() in self._unfolded_groups

    def row_role(self, index):
        """ C1 - 1st caption, C2 - 2nd caption, D - data """
        if index.row() == 0:
            return 'C1'
        elif index.row() == 1:
            return 'C2'
        else:
            return 'D'

    def row_min_id(self, irow):
        return self.dt.tab.rows[irow-2].id

    def column_role(self, index):
        """ I-id, C-category, D-data """
        return self.dt.column_role(index.column())

    def column_name(self, icol):
        return self.dt.visible_columns[icol].name

    def n_visible_categories(self):
        return self.dt.n_visible_categories()

    def visible_column_names(self):
        return [c.name for c in self.dt.visible_columns]

    def all_column_names(self):
        return list(self.dt.columns.keys())

    def has_collapses(self):
        for c in self.dt.columns.values():
            if hasattr(c, "_collapsed_categories"):
                return True
        return False

    def has_groups(self):
        return len(self.dt.group_by) > 0

    def n_filters(self):
        return len(self.dt.used_filters)

    def dt_type(self, index):
        return self.dt.visible_columns[index.column()].dt_type

    def use_coloring(self):
        return self.coloring.use

    def get_color_scheme(self):
        return self.coloring.color_scheme

    # ------------------------ modification procedures
    def add_filter(self, flt):
        self.dt.add_filter(flt)

    def rem_all_filters(self):
        self.dt.all_anon_filters.clear()
        self.dt.used_filters.clear()

    def group_rows(self, catnames, method=None):
        self.dt.group_by = copy.deepcopy(catnames)
        if method:
            self.dt.set_data_group_function(method)

    def unfold_row(self, index, do_unfold=None):
        ir = index.row()
        if do_unfold is None:
            isthere = self.is_unfolded(index)
            do_unfold = not isthere
        if isinstance(self._unfolded_groups, bool):
            if self._unfolded_groups:
                self._unfolded_groups = set(range(2, self.rowCount()))
            else:
                self._unfolded_groups = set()
            return self.unfold_row(index, do_unfold)
        else:
            if do_unfold:
                self._unfolded_groups.add(ir)
            else:
                self._unfolded_groups.remove(ir)
        self.dataChanged.emit(self.createIndex(ir, 0),
                              self.createIndex(ir, self.columnCount()))
        self.repr_updated.emit(self, ir)

    def unfold_all_rows(self, do_unfold):
        self._unfolded_groups = do_unfold
        self.view_update()

    def set_sorting(self, colname, is_asc):
        self.dt.ordering = (colname, 'ASC' if is_asc else 'DESC')

    def collapse_categories(self, what, do_hide, delim):
        """ what - list of column names or "all" special word
            returns newly created column or None
        """
        if what == 'all':
            cats = []
            for c in self.dt.columns.values():
                if c.is_category() and c.is_original() and c.name != 'id':
                    cats.append(c.name)
            return self.collapse_categories(cats, do_hide, delim)
        cols = [self.dt.columns[w] for w in what]
        ret = self.dt.merge_categories(cols, delim)
        if ret and do_hide:
            for c in ret.sql_delegate.deps:
                self.dt.set_visibility(c, False)
        return ret

    def remove_collapsed(self, what, do_show=True):
        """ removes collapsed column, show all categories which were collapsed

            what - list of column names of CollapsedCategories entries
                   or "all" special word
            do_show - whether to show all parent categories
            returns True if smth was removed
                    False otherwise
        """
        if what == 'all':
            cats = []
            for c in self.dt.columns.values():
                if not c.is_original() and\
                        c.sql_delegate.function_type == "collapsed_categories":
                    cats.append(c.name)
            return self.remove_collapsed(cats, do_show)
        if len(what) == 0:
            return False
        cols = [self.dt.columns[w] for w in what]
        showthis = set()
        for c in cols:
            for c2 in c.sql_delegate.deps:
                if c2 in self.dt.all_columns:
                    showthis.add(c2)
            self.dt.remove_column(c)
        for c in showthis:
            self.dt.set_visibility(c, True)
        return True

    def zoom_font(self, delta):
        self.conf._basic_font_size += delta
        self.conf.refresh()
        self.view_update()

    def switch_coloring_mode(self):
        self.coloring.use = not self.coloring.use
        self.conf.refresh()
        self.view_update()

    def set_coloring(self, column=None, scheme=None, is_local=None):
        if scheme is not None:
            self.coloring.color_scheme = scheme
        if column is not None:
            self.coloring.set_column(self.dt, column)
        if is_local is not None:
            self.coloring.absolute_limits = not is_local
        # here we call coloring.update()
        self.repr_updated.emit(self, -1)
