import os
import pathlib
import copy
import xml.etree.ElementTree as ET
from prog import basic
from prog import command
from prog import valuedict
from prog import filt
from bdata import dtab
from bdata import bcol
from bdata import convert


class ProjBackUp(object):
    def __init__(self, proj):
        self.proj = proj

        # backup tables
        self.ttab_names = []
        for tab in proj.data_tables:
            self.ttab_names.append(tab.ttab_name)
            tab.rename_ttab('_projbu{} {}'.format(basic.uniint(),
                                                  tab.ttab_name))

        # backup data
        self.data_tables = proj.data_tables[:]
        self._curname = proj._curname
        self._curdir = proj._curdir
        self.dictionaries = proj.dictionaries[:]
        self.named_filters = proj.named_filters[:]
        self.idc = copy.deepcopy(proj.idc)

        self.state_restored = False

    def clear(self):
        if not self.state_restored:
            for tab in self.data_tables:
                tab.destruct()
        self.data_tables = None
        self._curname = None
        self._curdir = None
        self.dictionaries = None
        self.named_filters = None
        self.idc = None

    def restore(self):
        for tab in self.proj.data_tables:
            tab.destruct()
        for nm, tab in zip(self.ttab_names, self.data_tables):
            tab.rename_ttab(nm)

        self.proj.data_tables = self.data_tables[:]
        self.proj._curname = self._curname
        self.proj._curdir = self._curdir
        self.proj.dictionaries = self.dictionaries[:]
        self.proj.named_filters = self.named_filters[:]
        self.proj.idc = copy.deepcopy(self.idc)

        self.state_restored = True


class NewDB(command.Command):
    def __init__(self, proj):
        super().__init__(proj=proj)

    def _exec(self):
        self._bu = ProjBackUp(self.proj)
        # detach
        if self.proj.sql.has_A:
            self.proj.sql.detach_database('A')
        # initialize proj
        self.proj.initialize()
        return True

    def _clear(self):
        self._bu.clear()

    def _undo(self):
        self._bu.restore()
        self._clear()


class LoadDB(command.Command):
    def __init__(self, proj, fname):
        super().__init__(proj=proj, fname=fname)

    def _exec(self):
        if not pathlib.Path(self.fname).exists():
            raise Exception('File not found {}'.format(self.fname))
        self._bu = ProjBackUp(self.proj)
        self.proj.sql.attach_database('A', self.fname)

        # database information
        self.proj.sql.query('SELECT "status" from A._INFO_')
        info = self.proj.sql.qresult()[0]
        info = ET.fromstring(info)

        # names
        self.proj._curname = info.find('PROJ').text
        self.proj._curdir = pathlib.Path(info.find('CWD').text)

        # dictionaries
        self.proj.dictionaries.clear()
        for dnd in info.findall('DICTIONARIES/E'):
            di = valuedict.Dictionary.from_xml(dnd)
            self.proj.add_dictionary(di)
        if len(self.proj.enum_dictionaries()) == 0:
            raise Exception(
                "No enum dictionaries were found at {}".format(self.fname))
        if len(self.proj.bool_dictionaries()) == 0:
            raise Exception(
                "No bool dictionaries were found at {}".format(self.fname))

        # named filters
        self.proj.named_filters.clear()
        for flt in info.findall('FILTERS/E'):
            f = filt.Filter.from_xml(flt)
            self.proj.add_filter(f)

        # tables
        self.proj.data_tables.clear()
        for tab in info.findall('TABLES/E'):
            t = dtab.DataTable.from_xml(tab, self.proj)
            self.proj.add_table(t)

        self.proj.set_current_filename(self.fname)
        self.proj.xml_loaded.emit(info)
        return True

    def _clear(self):
        self._bu.clear()

    def _undo(self):
        self._bu.restore()
        self._clear()


class SaveDBAs(command.Command):
    def __init__(self, proj, fname):
        super().__init__(proj=proj, fname=fname)

    def _exec(self):
        # 0) Detach A table first so that we can delete newfile even
        #    if it is used by this application
        if self.proj.sql.has_A:
            self._bu_current_a = self.proj._curname
            self.proj.sql.detach_database('A')
        else:
            self._bu_current_a = None

        # 1) delete newfile if it exists
        if pathlib.Path(self.fname).exists():
            os.remove(self.fname)

        # 2) open newfile as A database
        self.proj.sql.attach_database('A', self.fname)
        self.proj.set_current_filename(self.fname)

        # 3) create info database
        self.proj.sql.query('CREATE TABLE A._INFO_ ("status" TEXT)')
        self.proj.sql.query('INSERT INTO A._INFO_ ("status") VALUES (?)',
                            [('',)])

        # 4) commit
        self.proj.commit_all_changes()

        return True

    def _clear(self):
        self._bu_current_a = None

    def _undo(self):
        self.proj.sql.detach_database('A')

        if self._bu_current_a is not None:
            self.proj.sql.attach_database('A', self._bu_current_a)
            self.proj.set_current_filename(self._bu_current_a)
        else:
            self.proj.set_current_filename('New database')

        self._clear()


class NewTabCommand(command.Command):
    def __init__(self, proj):
        super().__init__(proj=proj)
        self.ttab_name = ''

    def _exec(self):
        self.atab = self._get_table()
        self.proj.add_table(self.atab)
        self.atab.update()
        return True

    def _clear(self):
        if self.ttab_name.startswith('_projbu'):
            self.atab.destruct()
            del self.atab

    def _undo(self):
        # backup sql table
        self.ttab_name = self.atab.ttab_name
        self.atab.rename_ttab('_projbu{} {}'.format(basic.uniint(),
                                                    self.atab.ttab_name))
        self.proj.data_tables.pop()

    def _redo(self):
        self.atab.rename_ttab(self.ttab_name)
        self.proj.add_table(self.atab)

    def _get_table(self):
        raise NotImplementedError


class AddDictionary(command.Command):
    def __init__(self, proj, dct):
        super().__init__(proj=proj, dct=dct)

    def _exec(self):
        self.proj.add_dictionary(self.dct)
        return True

    def _undo(self):
        self.proj.dictionaries.pop()


class AddFilter(command.Command):
    def __init__(self, proj, flt, usedtab):
        super().__init__(proj=proj, flt=flt, usedtab=usedtab)

    def _exec(self):
        if self.flt.name is not None:
            self.proj.add_filter(self.flt)
        for t in self.usedtab:
            if self.flt.name is None:
                t.add_anon_filter(self.flt)
            t.used_filters.append(self.flt.id)
        return True

    def _undo(self):
        for t in self.usedtab:
            if self.flt.name is None:
                t.all_anon_filters.pop()
            t.used_filters.pop()
        if self.flt.name is not None:
            self.proj.named_filters.pop()


class ApplyFilter(command.Command):
    def __init__(self, tab, flt):
        if not flt.is_applicable(tab):
            raise Exception("Filter {} is not applicable for table {}"
                            "".format(flt.name, tab.name))
        super().__init__(tab=tab, flt=flt)
        self.acts = []

    def _exec(self):
        if self.flt.id in self.tab.used_filters:
            return
        # add filter
        add = False
        if self.flt.name is None:
            if self.flt not in self.tab.all_anon_filters:
                add = True
        else:
            if self.flt not in self.tab.proj.named_filters:
                add = True
        if add is True:
            self.acts.append(command.ActFromCommand(
                AddFilter(self.tab.proj, self.flt, [self.tab])))
        else:
            a = basic.CustomObject()
            a.redo = lambda: self.tab.used_filters.append(self.flt.id)
            a.undo = lambda: self.tab.used_filters.pop()
            self.acts.append(a)
        self.acts[-1].redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()

    def _redo(self):
        for a in self.acts:
            a.redo()


class UnapplyFilter(command.Command):
    def __init__(self, tab, flts, rem_unused_anon):
        if flts == 'all':
            flts = [tab.get_filter(iden=x) for x in tab.used_filters]
        if isinstance(flts, filt.Filter):
            flts = [flts]
        super().__init__(tab=tab, flts=flts, rua=rem_unused_anon)

    def _exec(self):
        self.oldused = self.tab.used_filters[:]
        self.oldanon = self.tab.all_anon_filters[:]
        for f in self.flts:
            if f.id in self.tab.used_filters:
                self.tab.used_filters.remove(f.id)
            if self.rua and f in self.tab.all_anon_filters:
                self.tab.all_anon_filters.remove(f)
        return True

    def _undo(self):
        self.tab.used_filters = self.oldused
        self.tab.all_anon_filters = self.oldanon


class RemoveFilter(command.Command):
    def __init__(self, tab, flt):
        super().__init__()
        self.acts = []
        if flt.name is not None:
            self.acts.append(command.ActRemoveListEntry(
                    tab.proj.named_filters, flt))
        else:
            self.acts.append(command.ActRemoveListEntry(
                    tab.all_anon_filters, flt))
        for t in tab.proj.data_tables:
            if flt.id in t.used_filters:
                self.acts.append(command.ActRemoveListEntry(
                        t.used_filters, flt.id))

    def _exec(self):
        for a in self.acts:
            a.redo()
        return True

    def _undo(self):
        for a in reversed(self.acts):
            a.undo()


class ChangeDictionaries(command.Command):
    def __init__(self, proj, dctmap):
        """ dctmap - {'olddict name': newdict}
                      'olddict name': None    (for remove)
                      '__new__': [new dicts list]
        """
        super().__init__(proj=proj, dctmap=dctmap)
        self.acts = []

    def all_filters(self):
        ret = self.proj.named_filters[:]
        for t in self.proj.data_tables:
            ret.extend(t.all_anon_filters)
        return ret

    def act_remove_dictionary(self, dct):
        # filters
        for f in self.all_filters():
            if f.uses_dict(dct):
                self.act_remove_filter_anywhere(f)
        # columns
        for t in self.proj.data_tables:
            for c in t.all_columns:
                if c.uses_dict(dct):
                    self.act_newrepr_for_data_column(t, c, int)
        # remove dict
        a = command.ActRemoveListEntry(self.proj.dictionaries, dct)
        a.redo()
        self.acts.append(a)

    def act_remove_filter_anywhere(self, filt):
        if filt in self.proj.named_filters:
            a = command.ActRemoveListEntry(self.proj.named_filters, filt)
            a.redo()
            self.acts.append(a)
        for t in self.proj.data_tables:
            if filt in t.all_anon_filters:
                a = command.ActRemoveListEntry(t.all_anon_filters, filt)
                a.redo()
                self.acts.append(a)
            if filt.id in t.used_filters:
                a = command.ActRemoveListEntry(t.used_filters, filt.id)
                a.redo()
                self.acts.append(a)

    def act_change_filter_dict_name(self, filt, oname, nname):
        a = basic.CustomObject()
        a.redo = lambda: filt.change_dict_name(oname, nname)
        a.undo = lambda: filt.change_dict_name(nname, oname)
        a.redo()
        self.acts.append(a)

    def act_append_dictionary(self, dct):
        a = basic.CustomObject()
        a.redo = lambda: self.proj.add_dictionary(dct)
        a.undo = lambda: self.proj.dictionaries.pop()
        a.redo()
        self.acts.append(a)

    def act_convert_data_column(self, tab, column, newtp):
        conv1 = convert.TableConverter(tab)
        ci = conv1.colitem(column.name)
        assert isinstance(newtp, valuedict.Dictionary)
        if newtp.dt_type == 'ENUM':
            ci.new_repr = bcol.EnumRepr(newtp)
        else:
            ci.new_repr = bcol.BoolRepr(newtp)
        ci.conversation_options = 'keys to keys'

        com = convert.ConvertTable(conv1)
        a = basic.CustomObject()
        a.redo = lambda: com.do()
        a.undo = lambda: com.undo()
        a.redo()
        self.acts.append(a)

    def act_newrepr_for_data_column(self, tab, column, newtp):
        a = basic.CustomObject()
        if newtp is int:
            a.newrepr = bcol.IntRepr()
        elif isinstance(newtp, valuedict.Dictionary):
            a.newrepr = bcol.EnumRepr(newtp)
        else:
            assert False
        a.oldrepr = column.repr_delegate
        a.redo = lambda: column.set_repr_delegate(a.newrepr)
        a.undo = lambda: column.set_repr_delegate(a.oldrepr)
        a.redo()
        self.acts.append(a)

    def act_change_dictionary(self, target, source):
        a1 = command.ActRemoveListEntry(self.proj.dictionaries, target)
        a1.redo()
        self.acts.append(a1)
        self.act_append_dictionary(source)
        a2 = command.ActMoveListEntry(self.proj.dictionaries, source, a1.ind)
        a2.redo()
        self.acts.append(a2)

    def _exec(self):
        try:
            newd = self.dctmap['__new__']
            self.dctmap.pop('__new__')
        except KeyError:
            newd = []
        # 1) remove dictionaries
        for k in [k1 for k1, v1 in self.dctmap.items() if v1 is None]:
            d = self.proj.get_dictionary(k)
            self.act_remove_dictionary(d)

        # 2) change dictionaries
        for k, v in [(k1, v1) for k1, v1 in self.dctmap.items()
                     if v1 is not None]:
            d = self.proj.get_dictionary(k)
            what_changed = valuedict.Dictionary.compare(d, v)
            if 'keys added' in what_changed or 'keys removed' in what_changed:
                # remove filters
                for f in self.all_filters():
                    if f.uses_dict(d):
                        self.act_remove_filter_anywhere(f)
            elif 'name' in what_changed:
                # changed name in filters
                for f in filter(lambda x: x.uses_dict(d),
                                self.all_filters()):
                    self.act_change_filter_dict_name(f, d.name, v.name)
            # convert columns
            if 'keys added' in what_changed or 'keys removed' in what_changed:
                for t in self.proj.data_tables:
                    for c in filter(lambda x: x.uses_dict(d), t.all_columns):
                        self.act_convert_data_column(t, c, v)
            else:
                for t in self.proj.data_tables:
                    for c in filter(lambda x: x.uses_dict(d), t.all_columns):
                        self.act_newrepr_for_data_column(t, c, v)

        # 3) change dicts
        for k, v in self.dctmap.items():
            if v is not None:
                d = self.proj.get_dictionary(name=k)
                self.act_change_dictionary(d, v)

        # 4) add new dicts
        for d in newd:
            self.act_append_dictionary(d)
        return True

    def _undo(self):
        for a in self.acts[::-1]:
            a.undo()

    def _redo(self):
        for a in self.acts:
            a.redo()

    def _clear(self):
        self.acts.clear()
