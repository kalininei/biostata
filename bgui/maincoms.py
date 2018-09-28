import functools
import copy
from prog import basic
from prog import command
from prog import comproj
from bdata import funccol
from bdata import convert
from bgui import tmodel


class MainWinBU:
    def __init__(self, mainwin):
        self.mainwin = mainwin
        self.models = mainwin.models[:]
        self.tabframes = mainwin.tabframes[:]
        self.active_model = mainwin.active_model

    def clear(self):
        self.models = []
        self.tabframes = []
        self.active_model = None

    def restore(self):
        self.mainwin.models = self.models[:]
        self.mainwin.tabframes = self.tabframes[:]
        self.mainwin.active_model = self.active_model

        self.mainwin.wtab.clear()
        for f in self.mainwin.tabframes:
            self.mainwin.wtab.addTab(f, f.table_name())

        if len(self.models) > 0:
            ind = self.models.index(self.active_model)
            self.mainwin._set_active_model(ind)
            self.mainwin.wtab.setCurrentIndex(ind)
        else:
            self.mainwin._set_active_model(None)
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
        from bgui import tview
        if self.newmodel is None:
            self.newmodel = tmodel.TabModel(self.dt)
        if self.newframe is None:
            self.newframe = tview.TableView(self.mw.flow, self.newmodel,
                                            self.mw.wtab)

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
        self._unfolded_ids = None
        if not isinstance(mod._unfolded_groups, bool):
            self._unfolded_ids = set()
            for r in mod._unfolded_groups:
                self._unfolded_ids.add(mod.row_min_id(r))

    def redo(self):
        self.mod.update()
        # restore fold/unfold. After the update() _unfolded_groups is boolean
        if self._unfolded_ids is not None:
            for i in range(2, self.mod.rowCount()):
                if self.mod.row_min_id(i) in self._unfolded_ids:
                    index = self.mod.createIndex(i, 0)
                    self.mod.unfold_row(index, True)

    def undo(self):
        self.mod._unfolded_groups = self._bu_unfolded_groups
        self.mod.update(reset_opts=False)


class ComNewDatabase(command.Command):
    def __init__(self, mainwin):
        super().__init__(mw=mainwin)
        self._wbu = MainWinBU(mainwin)
        self.com = comproj.NewDB(self.mw.proj)
        self.mw = mainwin

    def _exec(self):
        self.com.do()
        self.mw._close_database()
        return True

    def _undo(self):
        self.com.undo()
        self._wbu.restore()


class ComLoadDatabase(command.Command):
    def __init__(self, mainwin, fname):
        super().__init__(mw=mainwin)
        self._wbu = MainWinBU(self.mw)
        self.com = comproj.LoadDB(self.mw.proj, fname)

    def _exec(self):
        self.com.do()
        self.mw.database_opened.emit()
        return True

    def _undo(self):
        self.com.undo()
        self._wbu.restore()


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
        self.mw.reset_title()
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
    def __init__(self, view, rw):
        super().__init__(aview=view, rw=rw)
        self.oldw = copy.deepcopy(self.aview.colwidth)

    def upd(self):
        self.aview._repr_changed()

    def _exec(self):
        for k, v in self.rw.items():
            self.aview.colwidth[k] = v
        self.upd()
        return True

    def _undo(self):
        self.aview.colwidth = copy.deepcopy(self.oldw)
        self.upd()


class ComFoldRows(command.Command):
    def __init__(self, tmod, rows, fold):
        super().__init__(tmod=tmod, rows=rows, fold=fold)
        self.acts = []
        self.fin_act = lambda: None

    def _exec(self):
        if self.fold is None:
            f1, f2 = None, None
        else:
            f1, f2 = self.fold, not self.fold
        if self.rows == 'all':
            assert self.fold is not None
            a = command.ActChangeAttr(self.tmod, '_unfolded_groups', f2)
            self.acts.append(a)
            self.fin_act = self.tmod.view_update
        else:
            for r in self.rows:
                ind = self.tmod.createIndex(r, 0)
                a = basic.CustomObject()
                a.redo = functools.partial(self.tmod.unfold_row, ind, f2)
                a.undo = functools.partial(self.tmod.unfold_row, ind, f1)
                self.acts.append(a)
        self._redo()
        return True

    def _redo(self):
        for a in self.acts:
            a.redo()
        self.fin_act()

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()
        self.fin_act()


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
        if len(self.mw.models) == 0:
            self.mw._set_active_model(None)


class ComSort(command.Command):
    def __init__(self, mod, icol, asc):
        super().__init__()
        colid = mod.dt.get_column(ivis=icol).id
        asc = 'ASC' if asc else 'DESC'
        self.act_update = ActModelUpdate(mod)
        self.act = command.ActChangeAttr(mod.dt, 'ordering', (colid, asc))

    def _exec(self):
        self.act.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        self.act.undo()
        self.act_update.undo()


class ComSetColumns(command.Command):
    def check_consistency(self, tmod, cols):
        for c in tmod.dt.all_columns[1:]:
            if c.is_original() and c not in cols:
                raise Exception("Can not remove original column {}"
                                "".format(c.name))

    def __init__(self, tmod, cols, isvis):
        super().__init__()
        self.check_consistency(tmod, cols)
        ac = [tmod.dt.all_columns[0]] + cols
        vc = [tmod.dt.all_columns[0]]
        for v, c in zip(isvis, cols):
            if v:
                vc.append(c)
        tmod.dt._fix_column_order(ac)
        tmod.dt._fix_column_order(vc)

        self.acts = []
        self.act_update = ActModelUpdate(tmod)

        self.acts.append(command.ActChangeAttr(tmod.dt, 'all_columns', ac))
        self.acts.append(command.ActChangeAttr(tmod.dt, 'visible_columns', vc))

    def _exec(self):
        for a in self.acts:
            a.redo()
        self.act_update.redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()
        self.act_update.redo()


class ComSetFilters(command.Command):
    def __init__(self, tmod, flts, used_flts):
        new_filters = []
        for f in filter(lambda x: x.name is None, flts):
            if f not in tmod.dt.all_anon_filters:
                new_filters.append(f)
        for f in filter(lambda x: x.name is not None, flts):
            if f not in tmod.dt.proj.named_filters:
                new_filters.append(f)

        rem_filters = []
        for f in tmod.dt.proj.named_filters:
            if f not in flts:
                rem_filters.append(f)
        for f in tmod.dt.all_anon_filters:
            if f not in flts:
                rem_filters.append(f)
        super().__init__(tmod=tmod, newf=new_filters, remf=rem_filters,
                         usedf=used_flts)
        self.acts = []
        self.act_update = ActModelUpdate(tmod)

    def _exec(self):
        for f in self.remf:
            self.acts.append(command.ActFromCommand(
                comproj.RemoveFilter(self.tmod.dt, f)))
            self.acts[-1].redo()
        for f in self.newf:
            self.acts.append(command.ActFromCommand(
                comproj.AddFilter(self.tmod.dt.proj, f, [self.tmod.dt])))
            self.acts[-1].redo()
        uf = [f.id for f in self.usedf]
        self.acts.append(command.ActChangeAttr(
                self.tmod.dt, 'used_filters', uf))
        self.acts[-1].redo()
        self.act_update.redo()
        return True

    def _redo(self):
        for a in self.acts:
            a.redo()
        self.act_update.redo()

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()
        self.act_update.undo()
