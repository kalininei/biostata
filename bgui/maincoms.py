import functools
import copy
from prog import basic
from prog import command
from prog import comproj
from bdata import funccol
from bdata import convert
from bgui import tmodel
from bgui import tview


class MainWinBU:
    def __init__(self, mainwin):
        self.mainwin = mainwin
        self.models = mainwin.models[:]
        self.tabframes = mainwin.tabframes[:]
        self.active_model = mainwin.active_model

    def clear(self):
        self.models = []
        self.tabframes = []
        self.active_model = []

    def restore(self):
        self.mainwin.models = self.models[:]
        self.mainwin.tabframes = self.tabframes[:]
        self.active_model = self.active_model

        self.mainwin.wtab.clear()
        for f in self.mainwin.tabframes:
            self.mainwin.wtab.addTab(f, f.table_name())

        self.mainwin.wtab.setCurrentIndex(self.mainwin.active_index())
        self.mainwin.reset_title()


class ActAddModel:
    def __init__(self, mainwin, dt, make_active):
        self.mw = mainwin
        self.dt = dt
        self.make_active = make_active
        self.newmodel = None
        self.newframe = None
        self.lastactive = None

    def redo(self):
        if self.newmodel is None:
            self.newmodel = tmodel.TabModel(self.dt)
        if self.newframe is None:
            self.newframe = tview.TableView(self.newmodel, self.mw.wtab)

        if self.mw.has_model():
            self.lastactive = self.mw.active_index()
        else:
            self.lastactive = None

        self.mw.models.append(self.newmodel)
        self.mw.tabframes.append(self.newframe)
        self.mw.wtab.addTab(self.newframe, self.newframe.table_name())
        if self.make_active:
            self.mw.wtab.setCurrentIndex(len(self.mw.models) - 1)

    def undo(self):
        if self.make_active and self.lastactive is not None:
            self.mw.wtab.setCurrentIndex(self.lastactive)
        self.mw.wtab.removeTab(self.mw.wtab.count()-1)
        self.mw.tabframes.pop()
        self.mw.models.pop()


class ActModelUpdate:
    def __init__(self, mod):
        self.mod = mod
        self._bu_unfolded_groups = copy.deepcopy(mod._unfolded_groups)

    def redo(self):
        self.mod.update()

    def undo(self):
        self.mod._unfolded_groups = self._bu_unfolded_groups
        self.mod.update()


class ComNewDatabase(comproj.NewDB):
    def __init__(self, mainwin):
        super().__init__(mainwin.proj)
        self._wbu = MainWinBU(mainwin)
        self.mw = mainwin

    def _exec(self):
        self.mw._close_database()
        return super()._exec(self)

    def _clear(self):
        self._wbu.clear()
        super()._clear()

    def _undo(self):
        super()._undo()
        self._wbu.restore()


# class ComLoadDatabase(comproj.LoadDB):
#     def __init__(self, mainwin, fname):
#         super().__init__(mainwin.proj, fname)
#         self._wbu = MainWinBU(mainwin)
#         self.mw._close_database()


class ComImport(command.Command):
    def __init__(self, mainwin, comimp):
        super().__init__(mw=mainwin, com=comimp)
        self.acts = []

    def _exec(self):
        self.acts.append(command.ActFromCommand(self.com))
        self.acts[-1].redo()
        self.acts.append(ActAddModel(self.mw,
                                     self.mw.proj.data_tables[-1],
                                     True))
        self.acts[-1].redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()

    def _redo(self):
        for a in self.acts:
            a.redo()

    def _clear(self):
        self.acts.clear()


class ComSaveDB(command.Command):
    def __init__(self, mainwin, fname):
        super().__init__(mw=mainwin, fname=fname)
        self.act = None

    def _exec(self):
        self.act = command.ActFromCommand(
                comproj.SaveDBAs(self.mw.proj, self.fname))
        self.act.redo()
        self.mw._set_actual_file(self.fname)
        self.mw.database_saved.emit()
        return True

    def _undo(self):
        self.act.undo()
        self.mw.reset_title()

    def _redo(self):
        self.act.redo()
        self.mw.reset_title()
        self.mw.database_saved.emit()


class ComChangeOpt(command.Command):
    def __init__(self, mainwin, kw):
        super().__init__(mw=mainwin, kw=kw)
        self.acts = []

    def _exec(self):
        for k, v in self.kw.items():
            self.acts.append(command.ActChangeAttr(self.mw.opts, k, v))
        self._redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()
        self.mw.reload_options()

    def _redo(self):
        for a in self.acts:
            a.redo()
        self.mw.reload_options()


class ComColumnWidth(command.Command):
    def __init__(self, mainwin, rw):
        super().__init__(mw=mainwin, rw=rw)
        self.oldw = copy.deepcopy(self.mw.active_tview().colwidth)
        self.amodel = lambda: mainwin.active_model
        self.aview = lambda: mainwin.active_tview()

    def upd(self):
        for i in range(self.amodel().columnCount()):
            self.aview().horizontalHeader().resizeSection(
                    i, self.aview()._get_column_width(i))

    def _exec(self):
        for k, v in self.rw.items():
            self.aview().colwidth[k] = v
        self.upd()
        return True

    def _undo(self):
        self.aview().colwidth = copy.deepcopy(self.oldw)
        self.upd()


class ComFoldRows(command.Command):
    def __init__(self, mainwin, rows, fold):
        super().__init__(mw=mainwin, rows=rows, fold=fold)
        self.acts = []

    def _exec(self):
        am = self.mw.active_model
        if self.rows == 'all':
            a = basic.CustomObject()
            a.redo = lambda: am.unfold_all_rows(not self.fold)
            a.undo = lambda: am.unfold_all_rows(self.fold)
            self.acts.append(a)
        else:
            for r in self.rows:
                a = basic.CustomObject()
                ind = am.createIndex(r, 0)
                a.redo = functools.partial(am.unfold_row, ind, not self.fold)
                a.undo = functools.partial(am.unfold_row, ind, self.fold)
                self.acts.append(a)
        self._redo()
        return True

    def _redo(self):
        for a in self.acts:
            a.redo()

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()


class ComToggleColoring(command.Command):
    def __init__(self, mod):
        super().__init__(mod=mod)

    def _exec(self):
        self.mod.switch_coloring_mode()
        return True

    def _undo(self):
        self.mod.switch_coloring_mode()


class ComSetColoring(command.Command):
    def __init__(self, mod, cn, cs, ilr):
        " tmodel, column name, ColorScheme Entry, is_local_range"
        super().__init__(mod=mod, cn=cn, cs=cs, ilr=ilr)

    def _exec(self):
        self.bu = (self.mod.coloring.color_by,
                   self.mod.coloring.color_scheme,
                   not self.mod.coloring.absolute_limits)
        self._redo()
        return True

    def _redo(self):
        self.mod.set_coloring(self.cn, self.cs, self.ilr)

    def _undo(self):
        self.mod.set_coloring(*self.bu)


class ComCollapseCategories(command.Command):
    def __init__(self, model, categories, delim, hide_source):
        super().__init__()
        self.act_merge = command.ActFromCommand(funccol.MergeCategories(
            model.dt, categories, delim, hide_source))
        self.act_update = ActModelUpdate(model)

    def _exec(self):
        self.act_merge.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        self.act_merge.undo()
        self.act_update.undo()


class ComRemoveCollapses(command.Command):
    def __init__(self, model):
        super().__init__(tmod=model)
        self.acts = []

    def _exec(self):
        for c in self.tmod.collapsed_categories_columns():
            self.acts.append(funccol.ActRemoveColumn(self.tmod.dt, c))
            self.acts[-1].redo()
            for c2 in c.sql_delegate.deps:
                self.acts.append(funccol.ActShowColumn(self.tmod.dt, c2))
                self.acts[-1].redo()
        self.act_update = ActModelUpdate(self.tmod)
        self.act_update.redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()
        self.act_update.undo()

    def _redo(self):
        for a in self.acts:
            a.redo()
        self.act_update.redo()


class ComGroupCats(command.Command):
    def __init__(self, tmod, cnames, method):
        super().__init__()
        self.act = command.ActFromCommand(
                funccol.GroupCategories(tmod.dt, cnames, method))
        self.act_update = ActModelUpdate(tmod)

    def _exec(self):
        self.act.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        self.act.undo()
        self.act_update.undo()


class ComAddFilter(command.Command):
    def __init__(self, tmod, flt):
        super().__init__()
        self.act = command.ActFromCommand(
                comproj.AddFilter(tmod.dt.proj, flt, [tmod.dt]))
        self.act_update = ActModelUpdate(tmod)

    def _exec(self):
        self.act.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        self.act.undo()
        self.act_update.undo()


class ComRemAllFilters(command.Command):
    def __init__(self, tmod):
        super().__init__()
        self.act = command.ActFromCommand(
            comproj.UnapplyFilter(tmod.dt, 'all', True))
        self.act_update = ActModelUpdate(tmod)

    def _exec(self):
        self.act.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        self.act.undo()
        self.act_update.undo()


class ComConvertColumns(command.Command):
    def __init__(self, mw, convs):
        super().__init__()
        self.act_update = ActModelUpdate(mw.active_model)
        self.acts = []
        for c in convs:
            self.acts.append(command.ActFromCommand(
                convert.ConvertTable(c)))

    def _exec(self):
        for a in self.acts:
            a.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()
        self.act_update.undo()


class ComChangeDictionaries(command.Command):
    def __init__(self, mw, ret):
        super().__init__()
        self.act = command.ActFromCommand(
            comproj.ChangeDictionaries(mw.proj, ret))
        if mw.has_model():
            self.act_update = ActModelUpdate(mw.active_model)
        else:
            self.act_update = command.ActNone()

    def _exec(self):
        self.act.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        self.act.undo()
        self.act_update.undo()


class ComAddTable(command.Command):
    def __init__(self, mainwin, dt):
        super().__init__()
        self.proj = mainwin.proj
        self.dt = dt
        self.act = ActAddModel(mainwin, dt, True)

    def _exec(self):
        self.proj.data_tables.append(self.dt)
        self.act.redo()
        return True

    def _undo(self):
        self.proj.data_tables.pop()
        self.act.undo()


class ComRemoveTable(command.Command):
    def __init__(self, mainwin, ind):
        super().__init__(mw=mainwin, ind=ind)
        self.acts = []
        self.proj = self.mw.proj
        self.tab = self.proj.data_tables[ind]
        self.tframe = self.mw.tabframes[ind]
        self.isactive = self.mw.active_index() == ind

    def _exec(self):
        self.acts.append(command.ActRemoveListEntry(
            self.proj.data_tables, self.proj.data_tables[self.ind]))
        self.acts.append(command.ActRemoveListEntry(
            self.mw.models, self.mw.models[self.ind]))
        self.acts.append(command.ActRemoveListEntry(
            self.mw.tabframes, self.mw.tabframes[self.ind]))

        a = basic.CustomObject()
        a.redo = lambda: self.mw.wtab.removeTab(self.ind)
        a.undo = lambda: self.mw.wtab.insertTab(self.ind, self.tframe,
                                                self.tframe.table_name())
        self.acts.append(a)
        self._redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()
        if self.isactive:
            self.mw.wtab.setCurrentIndex(self.ind)

    def _redo(self):
        for a in self.acts:
            a.redo()
        if len(self.mw.models) == 1:
            self.mw._set_active_model(None)
