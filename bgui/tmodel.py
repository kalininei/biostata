import copy
from bdata import dtab
from PyQt5 import QtCore


class TabModel(QtCore.QAbstractTableModel):
    def __init__(self, dt):
        super().__init__()
        self.dt = dt
        # False -- all are folded, True -- all are unfolded,
        # set() indicies of unfolded rows, which vanish at update()
        self._unfolded_groups = False

    def table_changed_subscribe(self, fun):
        self.dt.updated.add_subscriber(fun)

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

        if role == QtCore.Qt.UserRole:
            if index.row() > 1:
                return self.dt.get_raw_value(index.row()-2, index.column())
            else:
                return self.data(index, QtCore.QtDisplayRole)
        elif role == QtCore.Qt.DisplayRole:
            rr, cr = self.row_role(index), self.column_role(index)
            if rr == 'C1':
                if cr == 'I':
                    return "Id"
                elif cr == 'C':
                    return "Category"
                else:
                    return self.dt.table_name()
            elif rr == 'C2':
                return self.dt.column_caption(index.column())
            else:
                return self.dt.get_value(index.row()-2, index.column())

        return None

    def update(self):
        """ make a new query and recalculate the table """
        self.beginResetModel()
        self.dt.update()
        if not isinstance(self._unfolded_groups, bool):
            self._unfolded_groups = False
        self.endResetModel()

    # ------------------------ information procedures
    def table_name(self):
        return self.dt.table_name()

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

    def has_collapses(self):
        for c in self.dt.columns.values():
            if isinstance(c, dtab.CollapsedCategories):
                return True
        return False

    def has_groups(self):
        return len(self.dt.group_by) > 0

    def n_filters(self):
        return len(self.dt.filters)

    def dt_type(self, index):
        return self.dt.visible_columns[index.column()].dt_type

    # ------------------------ modification procedures
    def add_filters(self, flts):
        self.dt.filters.extend(flts)

    def rem_last_filter(self):
        self.dt.filters.pop()

    def rem_all_filters(self):
        self.dt.filters.clear()

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

    def unfold_all_rows(self, do_unfold):
        self._unfolded_groups = do_unfold
        self.modelReset.emit()

    def set_sorting(self, colname, is_asc):
        self.dt.ordering = (colname, 'ASC' if is_asc else 'DESC')

    def collapse_categories(self, what, do_hide=True):
        """ what - list of column names or "all" special word
            returns newly created column or None
        """
        if what == 'all':
            cats = []
            for c in self.dt.columns.values():
                if c.is_category and c.is_original and c.name != 'id':
                    cats.append(c.name)
            return self.collapse_categories(cats, do_hide)
        cols = [self.dt.columns[w] for w in what]
        ret = self.dt.merge_categories(cols)
        if ret and do_hide:
            for c in ret.parent:
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
                if isinstance(c, dtab.CollapsedCategories):
                    cats.append(c.name)
            return self.remove_collapsed(cats, do_show)
        if len(what) == 0:
            return False
        cols = [self.dt.columns[w] for w in what]
        showthis = set()
        for c in cols:
            for c2 in c.parent:
                showthis.add(c2)
            self.dt.remove_column(c)
        for c in showthis:
            self.dt.visible_columns.append(c)
        self.dt.resort_visible_categories()
        return True
