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
        try:
            self.ind = tab.visible_columns.index(col)
            self.col = col
            self.tab = tab
        except ValueError:
            self.ind = None

    def redo(self):
        if self.ind is not None:
            self.tab.visible_columns.pop(self.ind)

    def undo(self):
        if self.ind is not None:
            self.tab.visible_columns.insert(self.ind, self.col)


class MergeCategories(command.Command):
    def __init__(self, tab, catlist, delim, hide_source):
        cols = [tab.get_column(x) for x in catlist]
        assert len(cols) > 1
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
