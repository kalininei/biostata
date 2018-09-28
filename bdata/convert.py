import itertools
from bdata import bcol
from prog import basic
from prog import bsqlproc
from prog import command


class ColumnConverter:
    def __init__(self, tab, column):
        self.col = column
        self.table = tab
        self.proj = tab.proj
        self.acts = []
        self.discard()

    def set_acts(self, a):
        self.acts = a

    def discard(self):
        self.new_name = self.col.name
        self.new_comment = self.col.comment
        self.new_dim = self.col.dim
        self.new_repr = self.col.repr_delegate
        self.new_shortname = self.col.shortname
        self.conversation_options = ''
        self.do_remove = False

    def has_changes(self):
        if self.do_remove:
            return True
        if self.new_name != self.col.name:
            return True
        if self.new_comment != self.col.comment:
            return True
        if self.has_repr_changes():
            return True
        if self.new_dim != self.col.dim:
            return True
        if self.new_shortname != self.col.shortname:
            return True
        return False

    def need_alter(self):
        'should be run ALTER TABLE because of this column'
        if not self.col.is_original():
            return False
        else:
            return self.has_repr_changes() or self.do_remove or\
                    self.new_name != self.col.name

    def no_promote(self):
        'column can not be used a source column for functions and filters'
        return self.has_repr_changes() or self.do_remove

    def has_repr_changes(self):
        return not self.new_repr.same_representation(self.col.repr_delegate)

    def new_col_type(self):
        return self.new_repr.col_type()

    def type_conversation_string(self):
        if self.new_repr.same_representation(
                self.col.repr_delegate):
            return self.col.col_type()
        else:
            r = '{} ⇾ {}'.format(self.col.col_type(),
                                 self.new_repr.col_type())
            if self.conversation_options:
                r += "  /  " + self.conversation_options
            return r

    def set_conversation(self, conv_type):
        if conv_type is None:
            self.new_repr = self.col.repr_delegate
            self.conversation_options = ''
            return
        dct = None
        if conv_type[1]:
            dct = self.proj.get_dictionary(conv_type[1])
        new_repr = bcol._BasicRepr.default(conv_type[0], dct)
        if not new_repr.same_representation(self.col.repr_delegate):
            self.new_repr = new_repr
            self.conversation_options = conv_type[2]
        else:
            self.new_repr = self.col.repr_delegate
            self.conversation_options = ''

    def possible_conversations(self):
        ' -> totype, totype dict, options'
        ret = []
        if self.col.dt_type == 'INT':
            ret.append(['REAL', '', ''])
            ret.append(['TEXT', '', ''])
            ret.append(['ENUM', '', 'int to keys'])
            ret.append(['BOOL', '', 'int to keys'])
            if self.col.is_original():
                ret.append(['ENUM', '', 'int to values'])
                ret.append(['BOOL', '', 'int to values'])
        elif self.col.dt_type == 'REAL':
            ret.append(['INT', '', ''])
            ret.append(['TEXT', '', ''])
            ret.append(['ENUM', '', 'real to keys'])
            ret.append(['BOOL', '', 'real to keys'])
            if self.col.is_original():
                ret.append(['ENUM', '', 'real to values'])
                ret.append(['BOOL', '', 'real to values'])
        elif self.col.dt_type == 'TEXT':
            ret.append(['INT', '', ''])
            ret.append(['REAL', '', ''])
            ret.append(['ENUM', '', 'text to keys'])
            ret.append(['BOOL', '', 'text to keys'])
            if self.col.is_original():
                ret.append(['ENUM', '', 'text to values'])
                ret.append(['BOOL', '', 'text to values'])
        elif self.col.dt_type in ['ENUM', 'BOOL']:
            ret.append(['INT', '', 'keys to int'])
            ret.append(['TEXT', '', 'keys to text'])
            ret.append(['ENUM', '', 'keys to keys'])
            ret.append(['BOOL', '', 'keys to keys'])
            if self.col.is_original():
                ret.append(['INT', '', 'values to int'])
                ret.append(['TEXT', '', 'values to text'])
                ret.append(['ENUM', '', 'values to values'])
                ret.append(['BOOL', '', 'values to values'])
        return ret

    def conversation_to_string(self, conv):
        r = self.col.col_type() + ' ⇾ ' + conv[0]
        if conv[1]:
            r += '(' + conv[1] + ')'
        if conv[2]:
            r += '  /  ' + conv[2]
        return r

    def dictionary_prototype(self, convopt):
        keys, vals = [], []
        dv = self.table.get_distinct_column_raw_vals(
                self.col.name, True)
        if convopt.endswith('to keys'):
            for v in filter(lambda x: x is not None, dv):
                try:
                    keys.append(round(float(v)))
                except ValueError:
                    pass
            keys = list(sorted(set(keys)))
        elif convopt.endswith('to values'):
            for v in filter(lambda x: x is not None, dv):
                r = self.col.repr(v)
                if r is not None:
                    vals.append(str(r))
            vals = list(sorted(set(vals)))
        if len(keys) == 0:
            keys = list(range(len(vals)))
        if len(vals) == 0:
            vals = ['' for x in range(len(keys))]
        return keys, vals

    def apply(self):
        if not self.has_changes():
            return
        assert not self.col.is_original() or self.new_name == self.col.name,\
            "Original column names should be changed "\
            "within TableConverter.apply()"
        assert not self.col.is_original() or self.do_remove is False,\
            "Original columns should be removed within TableConverter.apply()"
        assert not self.col.is_original() or not self.has_repr_changes(),\
            "Original columns should be reformated "\
            "within TableConverter.apply()"

        if self.do_remove:
            self.act_remove_column()
            return
        if self.new_name != self.col.name:
            self.act_rename_column()
        if self.new_shortname != self.col.shortname:
            self.act_change_colattr('shortname', self.new_shortname)
        if self.new_dim != self.col.dim:
            self.act_change_colattr('dim', self.new_dim)
        if self.new_comment != self.col.comment:
            self.act_change_colattr('comment', self.new_comment)
        if self.has_repr_changes():
            self.act_set_new_repr()
            self.col.set_repr_delegate(self.new_repr)

    def act_rename_column(self):
        a = basic.CustomObject()
        a.oldname = self.col.name
        a.newname = self.new_name
        a.redo = lambda: self.col.rename(a.newname)
        a.undo = lambda: self.col.rename(a.oldname)
        a.redo()
        self.acts.append(a)

    def act_remove_column(self):
        a1 = command.ActRemoveListEntry(self.table.all_columns, self.col)
        a2 = command.ActRemoveListEntry(self.table.visible_columns, self.col)
        a1.redo()
        a2.redo()
        self.acts.extend([a1, a2])

    def act_change_colattr(self, attr, newattr):
        a = command.ActChangeAttr(self.col, attr, newattr)
        a.redo()
        self.acts.append(a)

    def act_set_new_repr(self):
        a = basic.CustomObject()
        a.old_repr = self.col.repr_delegate
        a.new_repr = self.new_repr
        a.redo = lambda: self.col.set_repr_delegate(a.new_repr)
        a.undo = lambda: self.col.set_repr_delegate(a.old_repr)
        a.redo()
        self.acts.append(a)

    def internal_repr_change_line(self):
        assert self.col.is_original()
        sline = self.col.sql_line(False)
        if not self.has_repr_changes():
            return sline
        # ================ INT
        if self.col.dt_type == 'INT':
            # to real
            if isinstance(self.new_repr, bcol.RealRepr):
                return 'CAST({} AS REAL)'.format(sline)
            # to text
            elif isinstance(self.new_repr, bcol.TextRepr):
                return 'CAST({} AS TEXT)'.format(sline)
            # to enum, bool
            elif isinstance(self.new_repr, bcol.EnumRepr):
                if self.conversation_options.endswith('to keys'):
                    ivals = ', '.join(map(str, self.new_repr.dict.keys()))
                    return 'CASE WHEN {0} IN ({1}) THEN {0} '\
                           'ELSE NULL END'.format(sline, ivals)
                elif self.conversation_options.endswith('to values'):
                    qr = 'CASE '
                    for k, v in self.new_repr.dict.kvalues.items():
                        a = "WHEN CAST({} AS TEXT)='{}' THEN {} ".format(
                            sline, v, k)
                        qr = qr + a
                    return qr + 'ELSE NULL END'
        # ================ REAL
        elif self.col.dt_type == 'REAL':
            # to int
            if isinstance(self.new_repr, bcol.IntRepr):
                return 'CAST(ROUND({}) AS INTEGER)'.format(sline)
            # to text
            elif isinstance(self.new_repr, bcol.TextRepr):
                return 'CAST({} AS TEXT)'.format(sline)
            # to enum, bool
            elif isinstance(self.new_repr, bcol.EnumRepr):
                if self.conversation_options.endswith('to keys'):
                    ivals = ', '.join(map(str, self.new_repr.dict.keys()))
                    return 'CASE WHEN cast_real_to_int({0}) IN ({1}) '\
                           'THEN cast_real_to_int({0}) '\
                           'ELSE NULL END'.format(sline, ivals)
                elif self.conversation_options.endswith('to values'):
                    qr = 'CASE '
                    for k, v in self.new_repr.dict.kvalues.items():
                        a = "WHEN CAST({} AS TEXT)='{}' THEN {} ".format(
                            sline, v, k)
                        qr = qr + a
                    return qr + 'ELSE NULL END'
        # ================ TEXT
        elif self.col.dt_type == 'TEXT':
            # to int
            if isinstance(self.new_repr, bcol.IntRepr):
                return 'cast_txt_to_int({})'.format(sline)
            # to real
            elif isinstance(self.new_repr, bcol.RealRepr):
                return 'cast_txt_to_real({})'.format(sline)
            # to enum, bool
            elif isinstance(self.new_repr, bcol.EnumRepr):
                if self.conversation_options.endswith('to keys'):
                    ivals = ', '.join(map(str, self.new_repr.dict.keys()))
                    return 'CASE WHEN cast_txt_to_int({0}) IN ({1}) '\
                           'THEN cast_txt_to_int({0}) '\
                           'ELSE NULL END'.format(sline, ivals)
                elif self.conversation_options.endswith('to values'):
                    qr = 'CASE '
                    for k, v in self.new_repr.dict.kvalues.items():
                        a = "WHEN CAST({} AS TEXT)='{}' THEN {} ".format(
                            sline, v, k)
                        qr = qr + a
                    return qr + 'ELSE NULL END'
        # ============= [ENUM, BOOL] as KEYS
        elif self.col.dt_type in ['ENUM', 'BOOL'] and\
                self.conversation_options.startswith('keys'):
            # to int
            if isinstance(self.new_repr, bcol.IntRepr):
                return sline
            # to real
            elif isinstance(self.new_repr, bcol.RealRepr):
                return 'CAST({} AS REAL)'.format(sline)
            # to text
            elif isinstance(self.new_repr, bcol.TextRepr):
                return 'CAST({} AS TEXT)'.format(sline)
            # to enum, bool
            elif isinstance(self.new_repr, bcol.EnumRepr):
                assert self.conversation_options == 'keys to keys'
                ivals = ', '.join(map(str, self.new_repr.dict.keys()))
                return 'CASE WHEN {0} IN ({1}) THEN {0} '\
                       'ELSE NULL END'.format(sline, ivals)
        # ============= [ENUM, BOOL] as VALUES
        elif self.col.dt_type in ['ENUM', 'BOOL'] and\
                self.conversation_options.startswith('values'):
            # to int
            if isinstance(self.new_repr, bcol.IntRepr):
                qr = ''
                for k, v in self.col.repr_delegate.dict.kvalues.items():
                    v = bsqlproc.cast_txt_to_int(v)
                    if v is not None:
                        a = "WHEN {}={} THEN {} ".format(sline, k, v)
                        qr = qr + a
                return 'CASE ' + qr + 'ELSE NULL END' if qr else 'NULL'
            # to real
            elif isinstance(self.new_repr, bcol.RealRepr):
                qr = ''
                for k, v in self.col.repr_delegate.dict.kvalues.items():
                    v = bsqlproc.cast_txt_to_real(v)
                    if v is not None:
                        a = "WHEN {}={} THEN {} ".format(sline, k, v)
                        qr = qr + a
                return 'CASE ' + qr + 'ELSE NULL END' if qr else 'NULL'
            # to text
            elif isinstance(self.new_repr, bcol.TextRepr):
                qr = ''
                for k, v in self.col.repr_delegate.dict.kvalues.items():
                    a = "WHEN {}={} THEN '{}' ".format(sline, k, v)
                    qr = qr + a
                return 'CASE ' + qr + 'ELSE NULL END' if qr else 'NULL'
            # to enum, bool
            elif isinstance(self.new_repr, bcol.EnumRepr):
                assert self.conversation_options == 'values to values'
                d1, d2 = self.col.repr_delegate.dict, self.new_repr.dict
                pairs = []
                for (k1, k2) in itertools.product(d1.keys(), d2.keys()):
                    if d1.key_to_value(k1) == d2.key_to_value(k2):
                        pairs.append((k1, k2))
                qr = ''
                for k1, k2 in pairs:
                    qr += "WHEN {}={} THEN {} ".format(sline, k1, k2)
                return 'CASE ' + qr + 'ELSE NULL END' if qr else 'NULL'
        assert False, "{} {}".format(self.col.dt_type, self.new_repr)


class TableConverter:
    def __init__(self, tab):
        self.table = tab
        self.proj = tab.proj
        self.citems = [ColumnConverter(tab, c)
                       for c in tab.all_columns][1:]
        self.discard()
        self.acts = []

    def set_acts(self, a):
        self.acts = a
        for c in self.citems:
            c.set_acts(a)

    def colitem(self, cname):
        for c in self.citems:
            if c.col.name == cname:
                return c
        raise KeyError

    def discard(self):
        self.new_name = self.table.name
        self.new_comment = self.table.comment
        self.do_remove = False

    def full_discard(self):
        self.discard()
        for it in self.citems:
            it.discard()

    def has_changes(self):
        if self.do_remove:
            return True
        if self.new_name != self.table.name:
            return True
        if self.new_comment != self.table.comment:
            return True
        for c in self.citems:
            if c.has_changes():
                return True
        return False

    def act_remove_table(self):
        a = command.ActRemoveListEntry(self.proj.data_tables, self.table)
        a.redo()
        self.acts.append(a)

    def apply(self):
        if not self.has_changes():
            return
        # -------------- Table edit
        # remove table
        if self.do_remove:
            self.act_remove_table()
            return
        # change table name
        if self.new_name != self.table.name:
            a = command.ActChangeAttr(self.table, 'name', self.new_name)
            a.redo()
            self.acts.append(a)
        # change comments
        if self.new_comment != self.table.comment:
            a = command.ActChangeAttr(self.table, 'comment', self.new_comment)
            a.redo()
            self.acts.append(a)

        # -------------- Columns edit
        # additional removes
        for c in self.implicit_removes():
            c.do_remove = True

        # anon filters adjust
        for f in self.table.all_anon_filters[:]:
            self.adjust_filter(f)

        # change name/remove/reformat for original columns
        cnitems = [c for c in self.citems if c.need_alter()]
        if len(cnitems) > 0:
            self._alter_origs()
            # remove deleted from citems
            self.citems = [c for c in self.citems
                           if not c.col.is_original() or not c.do_remove]

        # change columns
        for c in self.citems:
            c.apply()

        # remove deleted from citems
        self.citems = [c for c in self.citems if not c.do_remove]

        self._final_reassemble()

    def act_change_filter_column_name(self, flt, oname, nname):
        a = basic.CustomObject()
        a.redo = lambda: flt.change_column_name(oname, nname)
        a.undo = lambda: flt.change_column_name(nname, oname)
        a.redo()
        self.acts.append(a)

    def adjust_filter(self, flt):
        """ if the filter can not be used anymore returns False
            and removes it from used_filters
        """
        tab = self.table
        # removes
        for c in filter(lambda x: x.no_promote(), self.citems):
            if flt.uses_column(c.col):
                a1 = command.ActRemoveListEntry(tab.all_anon_filters, flt)
                a2 = command.ActRemoveListEntry(tab.used_filters, flt.id)
                a1.redo()
                a2.redo()
                self.acts.extend([a1, a2])
        # new names
        for c in filter(lambda x: x.new_name != x.col.name, self.citems):
            if flt.uses_column(c.col):
                self.act_change_filter_column_name(flt, c.col.name, c.new_name)

    def implicit_removes(self):
        'remove columns which depend on removed or repr_changed columns'
        ret = [c for c in self.citems if c.no_promote()]
        candidates = [c for c in self.citems
                      if not c.no_promote() and isinstance(
                          c.col.sql_delegate, bcol.FuncSqlDelegate)]
        iorig = len(ret)
        i = 0
        while i < len(ret):
            for it in candidates:
                # append implicitly removed column
                if ret[i].col in it.col.sql_delegate.deps:
                    ret.append(it)
                    candidates.remove(it)
                    break
            else:
                i += 1

        return ret[iorig:]

    def _alter_origs(self):
        oitems = [x for x in self.citems if x.col.is_original()]

        # remove columns
        for it in filter(lambda x: x.do_remove, oitems):
            it.act_remove_column()

        # rename columns by: alter to tmp, create new, copy, drop tmp
        colnames_before = self.table._original_collist(False)
        for i, cb in enumerate(colnames_before):
            cn = cb[1:-1]
            if not cn.startswith('_status'):
                try:
                    itm = self.colitem(cn)
                    # here we add casting functions for
                    # internal representation
                    colnames_before[i] = itm.internal_repr_change_line()
                except KeyError:
                    pass

        # rename/change representation for new table columns
        for c in oitems:
            if c.new_name != c.col.name:
                c.act_rename_column()
            if c.has_repr_changes():
                c.act_set_new_repr()

        # if internal representation doesn't change => exit
        colnames_after = self.table._original_collist(False)
        if basic.list_equal(colnames_after, colnames_before):
            return

        class Act:
            def __init__(self, tab, cnbefore, cnafter):
                self.tab = tab
                self.proj = tab.proj
                self.tmpname = '_alter{} {}'.format(basic.uniint(),
                                                    self.tab.ttab_name)
                qr = 'ALTER TABLE "{}" RENAME TO "{}"'.format(
                        self.tab.ttab_name, self.tmpname)
                self.tab.query(qr)
                self.tab._create_ttab()
                qr = 'INSERT INTO "{}" ({}) SELECT {} FROM "{}"'.format(
                    self.tab.ttab_name,
                    ', '.join(cnafter),
                    ', '.join(cnbefore),
                    self.tmpname)
                self.tab.query(qr)

            def undo(self):
                self.proj.sql.swap_tables(self.tmpname, self.tab.ttab_name)

            def redo(self):
                self.proj.sql.swap_tables(self.tmpname, self.tab.ttab_name)

            def __del__(self):
                self.tab.query('DROP TABLE "{}"'.format(self.tmpname))

        a = Act(self.table, colnames_before, colnames_after)
        self.acts.append(a)

    def act_fix_column_order(self, clist):
        ind1, ind2 = [], []
        for i, c in enumerate(clist):
            if c.is_category():
                ind1.append(i)
            else:
                ind2.append(i)
        a = command.ActReorderList(clist, ind1 + ind2)
        a.redo()
        self.acts.append(a)

    def _final_reassemble(self):
        # table.columns dictionary
        # check columns ordering in case of data types transitions
        # between categorical and real.
        self.act_fix_column_order(self.table.all_columns)
        self.act_fix_column_order(self.table.visible_columns)

        for f in self.table.used_filters[:]:
            flt = self.table.get_filter(iden=f)
            if not flt.is_applicable(self.table):
                a = command.ActRemoveListEntry(self.table.used_filters, f)
                a.redo()
                self.acts.append(a)


class ConvertTable(command.Command):
    def __init__(self, conv):
        super().__init__(conv=conv)
        self.acts = []

    def _exec(self):
        self.conv.set_acts(self.acts)
        self.conv.apply()
        return True

    def _undo(self):
        for a in self.acts[::-1]:
            a.undo()

    def _redo(self):
        for a in self.acts:
            a.redo()

    def _clear(self):
        self.acts.clear()
