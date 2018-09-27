from prog import command
from bdata import bcol


class ActAddColumn:
    def __init__(self, tab, col):
        self.tab = tab
        self.col = col
        if col.id == -1:
            col.set_id(self.tab.proj.new_id())
        if self.col.is_category():
            for self.ind1 in range(len(tab.all_columns)):
                if not tab.all_columns[self.ind1].is_category():
                    break
            else:
                self.ind1 += 1
            for self.ind2 in range(len(tab.visible_columns)):
                if not tab.visible_columns[self.ind2].is_category():
                    break
            else:
                self.ind2 += 1
        else:
            self.ind1 = len(self.tab.all_columns)
            self.ind2 = len(self.tab.visible_columns)

    def redo(self):
        self.tab.all_columns.insert(self.ind1, self.col)
        self.tab.visible_columns.insert(self.ind2, self.col)

    def undo(self):
        self.tab.all_columns.pop(self.ind1)
        self.tab.visible_columns.pop(self.ind2)


class ActHideColumn:
    def __init__(self, tab, col):
        assert col in tab.all_columns
        self.col = col
        self.tab = tab
        try:
            self.ind = tab.visible_columns.index(col)
        except ValueError:
            self.ind = None

    def redo(self):
        if self.ind is not None:
            self.tab.visible_columns.pop(self.ind)

    def undo(self):
        if self.ind is not None:
            self.tab.visible_columns.insert(self.ind, self.col)


class ActRemoveColumn:
    def __init__(self, tab, col):
        assert not col.is_original()
        self.tab = tab
        self.col = col
        try:
            self.ind1 = tab.all_columns.index(col)
        except ValueError:
            self.ind1 = None
        try:
            self.ind2 = tab.visible_columns.index(col)
        except ValueError:
            self.ind2 = None

    def redo(self):
        if self.ind1 is not None:
            self.tab.all_columns.pop(self.ind1)
        if self.ind2 is not None:
            self.tab.visible_columns.pop(self.ind2)

    def undo(self):
        if self.ind1 is not None:
            self.tab.all_columns.insert(self.ind1, self.col)
        if self.ind2 is not None:
            self.tab.visible_columns.insert(self.ind2, self.col)


class ActShowColumn:
    def __init__(self, tab, col):
        assert col in tab.all_columns
        self.tab = tab
        self.col = col
        if col not in tab.visible_columns:
            iat = tab.all_columns.index(col) - 1
            while tab.all_columns[iat] not in tab.visible_columns:
                iat -= 1
            self.ind = tab.visible_columns.index(tab.all_columns[iat]) + 1
        else:
            self.ind = None

    def redo(self):
        if self.ind is not None:
            self.tab.visible_columns.insert(self.ind, self.col)

    def undo(self):
        if self.ind is not None:
            self.tab.visible_columns.pop(self.ind)


class MergeCategories(command.Command):
    def __init__(self, tab, catlist, delim, hide_source):
        assert len(catlist) > 1
        if catlist == 'all':
            cols = list(filter(lambda x: x.is_category(), tab.all_columns))[1:]
        else:
            cols = [tab.get_column(x) for x in catlist]
        assert all([x.is_category() for x in cols])
        super().__init__(tab=tab, cols=cols, delim=delim,
                         hide_source=hide_source)
        self.acts = []

    def _exec(self):
        self.new_col = bcol.collapsed_categories(self.cols, self.delim)
        self.acts.append(ActAddColumn(self.tab, self.new_col))
        self.acts[-1].redo()
        if self.hide_source:
            for c in self.cols:
                self.acts.append(ActHideColumn(self.tab, c))
                self.acts[-1].redo()
        return True

    def _clear(self):
        self.new_col = None

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()

    def _redo(self):
        for a in self.acts:
            a.redo()


class GroupCategories(command.Command):
    @staticmethod
    def data_group_function(method):
        if method == 'amean':
            return "AVG"
        elif method == 'max':
            return "MAX"
        elif method == 'min':
            return "MIN"
        elif method == 'median':
            return "median"
        elif method == 'median+':
            return "medianp"
        elif method == 'median-':
            return "medianm"
        else:
            raise NotImplementedError

    def __init__(self, tab, catlist, method):
        col = [tab.get_column(x) for x in catlist]
        f = GroupCategories.data_group_function(method)
        super().__init__(tab=tab, col=col, fun=f)
        self.acts = []

    def _exec(self):
        ids = [x.id for x in self.col]
        self.acts.append(
            command.ActChangeAttr(self.tab, 'group_by', ids))
        for x in self.tab.all_columns:
            if not x.is_category():
                self.acts.append(
                    command.ActChangeAttr(x, 'real_data_groupfun', self.fun))
        self._redo()
        return True

    def _clear(self):
        self.acts = []

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()

    def _redo(self):
        for a in self.acts:
            a.redo()
