import collections
import itertools
from bdata import dtab
from bdata import bcol


class DerivedTable(dtab.DataTable):
    """ Table derived from a set of other tables """
    def __init__(self, name, origtables, proj):
        self.dependencies = origtables
        super().__init__(name, proj)

    def _insert_query(self, origquery):
        """ called after self.columns was built
        """
        sqlcols, sqlcols2 = [], []
        for c in itertools.islice(self.columns.values(), 1, None):
            sqlcols.append(c.sql_line())
            sqlcols2.append(c.status_column.sql_line())
        qr = 'INSERT INTO "{tabname}" ({collist}) {select_from_orig}'.format(
                tabname=self.ttab_name,
                collist=", ".join(itertools.chain(sqlcols, sqlcols2)),
                select_from_orig=origquery)
        self.query(qr)


class CopyViewTable(DerivedTable):
    """ Table derived as a copy of a current view of another table
    """
    def __init__(self, name, origtab, cols, proj):
        """ origtab - DataTable
            cols - OrderedDict {origname: newname}
        """
        self._given_cols_names = list(cols.values())
        self._given_cols_list = [origtab.columns[x] for x in cols.keys()]
        super().__init__(name, [origtab], proj)

        # explicit copies
        self._default_group_method = self.dependencies[0]._default_group_method

    def _init_columns(self):
        self.__merged_valdata = {}
        self.columns = collections.OrderedDict()
        self.columns['id'] = bcol.build_id()
        for k, v in zip(self._given_cols_names, self._given_cols_list):
            col = bcol.build_deep_copy(v, k)
            self.columns[k] = col
        self._complete_columns_lists()

    def _fill_ttab(self):
        # build a query to the original table
        origquery = self.dependencies[0]._compile_query(
                cols=self._given_cols_list,
                status_adds=True,
                group_adds=False)

        self._insert_query(origquery)


class JoinTable(DerivedTable):
    class TableEntry:
        """ return value entry """
        def __init__(self, tabname):
            self.tabname = tabname
            self.view_columns = []
            self.name_columns = []
            self.key_columns = []
            self.key_mappings = []

        def add_view_column(self, name, retname=None):
            if retname is None:
                retname = name
            self.view_columns.append(name)
            self.name_columns.append(retname)

        def add_key_column(self, name):
            self.key_columns.append(name)
            self.key_mappings.append(lambda x: x)

    def __init__(self, name, joinentries, proj):
        tabnames = [x.tabname for x in joinentries]
        tabs = [proj.get_table(x) for x in tabnames]
        self.joinentries = joinentries
        super().__init__(name, tabs, proj)

    def _init_columns(self):
        self.columns = collections.OrderedDict()
        self.columns['id'] = bcol.build_id()
        for te, table in zip(self.joinentries, self.dependencies):
            for onm, tnm in zip(te.view_columns, te.name_columns):
                ocol = table.columns[onm]
                self.columns[tnm] = bcol.build_deep_copy(ocol, tnm)

    def _fill_ttab(self):
        # 1. temporary add comparison columns
        for te, table in zip(self.joinentries, self.dependencies):
            for i, kcol, kfun in zip(itertools.count(1),
                                     te.key_columns,
                                     te.key_mappings):
                depcol = table.columns[kcol]
                newcol = bcol.build_function_column("__k{}".format(i), kfun,
                                                    [depcol], False, "INT")
                table.add_column(newcol)
        # 2. build table queries
        tabqueries = []
        for j, te, table in zip(itertools.count(1),
                                self.joinentries, self.dependencies):
            cols = [table.columns[x] for x in te.view_columns]
            for i in range(len(te.key_columns)):
                cols.append(table.columns["__k{}".format(i+1)])
            tabqueries.append("({1}) __t{0}".format(j, table._compile_query(
                cols,
                status_adds=True,
                group_adds=False,
                auto_alias="__c")))
        # 3. Build ON lines
        onlines = []
        for i in range(len(self.joinentries)-1):
            first_ki = len(self.joinentries[i].view_columns) + 1
            first_kj = len(self.joinentries[i+1].view_columns) + 1
            s = []
            for k in range(len(self.joinentries[i].key_columns)):
                s.append("__t{}.__c{} = __t{}.__c{}".format(i+1, first_ki+k,
                                                            i+2, first_kj+k))
            onlines.append("ON " + " AND ".join(s))
        # 4. Build SELECT line
        sellines = []
        # data columns
        for itab in range(len(self.joinentries)):
            for icol in range(len(self.joinentries[itab].view_columns)):
                sellines.append("__t{}.__c{}".format(itab+1, icol+1))
        # status columns
        for itab in range(len(self.joinentries)):
            st = len(self.joinentries[itab].view_columns)\
                + len(self.joinentries[itab].key_columns)
            for icol in range(len(self.joinentries[itab].view_columns)):
                sellines.append("__t{}.__c{}".format(itab+1, st+icol+1))

        selline = "SELECT " + ", ".join(sellines)
        # 5. Assemble origquery
        s = [selline, "FROM", tabqueries[0]]
        for i in range(len(self.joinentries)-1):
            s.extend(["INNER JOIN", tabqueries[i+1], onlines[i]])
        origquery = "\n".join(s)

        # 6. insert
        self._insert_query(origquery)

        # 7. remove comparison columns
        for table in self.dependencies:
            for i, kcol in zip(itertools.count(1), te.key_columns):
                col = table.columns["__k{}".format(i)]
                table.remove_column(col)

        self._complete_columns_lists()


class ExplicitTable(DerivedTable):
    def __init__(self, name, colformats, tab, proj):
        """ colformats = [(name, dt_type, dict), ...]
            tab[][] - table in python types format. None for NULL.
        """
        self.colformats = colformats
        self._input_tab = tab
        super().__init__(name, [], proj)

    def _init_columns(self):
        self.columns = collections.OrderedDict()
        self.columns['id'] = bcol.build_id()
        for name, dt_type, dict_name in self.colformats:
            col = bcol.explicit_build(self.proj, name, dt_type, dict_name)
            self.columns[name] = col
        del self.colformats

    def _fill_ttab(self):
        sqlcols = []
        for c in itertools.islice(self.columns.values(), 1, None):
            sqlcols.append(c.sql_line())
        pholders = ','.join(['?'] * (len(self.columns)-1))
        qr = 'INSERT INTO "{tabname}" ({collist}) VALUES ({ph})'.format(
                tabname=self.ttab_name,
                collist=", ".join(sqlcols),
                ph=pholders)
        print(qr)
        self.cursor.executemany(qr, self._input_tab)

        del self._input_tab

        self._complete_columns_lists()
