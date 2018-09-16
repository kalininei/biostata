import collections
import itertools
from bdata import dtab
from bdata import bcol


def _insert_query(self, origquery):
    """ Fill self.ttab_name with table built by origquery.
        Origquery should return chain(columns, status_columns) in order
        defined by self.columns """
    sqlcols, sqlcols2 = [], []
    for c in itertools.islice(self.columns.values(), 1, None):
        sqlcols.append(c.sql_line())
        sqlcols2.append(c.status_column.sql_line())
    qr = 'INSERT INTO "{tabname}" ({collist}) {select_from_orig}'.format(
            tabname=self.ttab_name,
            collist=", ".join(itertools.chain(sqlcols, sqlcols2)),
            select_from_orig=origquery)
    self.query(qr)
    self.reset_id()


# ============================== Original table
def original_table(tab_name, proj):

    def init_columns(self):
        self.columns = collections.OrderedDict()
        self.query('SELECT colname from A."_COLINFO {}"'.format(self.name))
        id_found = False
        for v in self.qresults():
            if v[0] == 'id':
                id_found = True
                col = bcol.build_id()
            else:
                col = bcol.build_from_db(self.proj, self, v[0])
            self.columns[col.name] = col
        if not id_found:
            raise Exception("unique id column was not found")

    def fill_ttab(self):
        ls = [x.sql_line() for x in self.columns.values() if x.is_original()]
        qr = 'INSERT INTO "{0}" ({1}) SELECT {1} from "{2}"'.format(
            self.ttab_name,
            ", ".join(ls),
            self.name)
        self.query(qr)

    return dtab.DataTable(tab_name, proj, init_columns, fill_ttab, True)


# ============================= CopyView table
def copy_view_table(tab_name, origtab, cols, proj):
    """ Table derived as a copy of a current view of another table
    """
    _given_cols_names = list(cols.values())
    _given_cols_list = [origtab.columns[x] for x in cols.keys()]

    def init_columns(self):
        self.columns = collections.OrderedDict()
        self.columns['id'] = bcol.build_id()
        for k, v in zip(_given_cols_names, _given_cols_list):
            col = bcol.build_deep_copy(v, k)
            self.columns[k] = col

    def fill_ttab(self):
        # build a query to the original table
        origquery = origtab._compile_query(
                cols=_given_cols_list,
                status_adds=True,
                group_adds=False)

        _insert_query(self, origquery)

    ret = dtab.DataTable(tab_name, proj, init_columns, fill_ttab, False)

    # explicit copies
    ret._default_group_method = origtab._default_group_method

    return ret


# ============================== JoinTable
class JoinTableEntry:
    """ A value entry for join procedure"""
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


def join_table(tab_name, joinentries, proj):
    """ builds a join table from joinentries of JoinTableEntry class
    """
    tabnames = [x.tabname for x in joinentries]
    tabs = [proj.get_table(x) for x in tabnames]

    def init_columns(self):
        self.columns = collections.OrderedDict()
        self.columns['id'] = bcol.build_id()
        for te, table in zip(joinentries, tabs):
            for onm, tnm in zip(te.view_columns, te.name_columns):
                ocol = table.columns[onm]
                self.columns[tnm] = bcol.build_deep_copy(ocol, tnm)

    def fill_ttab(self):
        # 1. temporary add comparison columns
        for te, table in zip(joinentries, tabs):
            for i, kcol, kfun in zip(itertools.count(1),
                                     te.key_columns,
                                     te.key_mappings):
                depcol = table.columns[kcol]
                newcol = bcol.build_function_column("__k{}".format(i), kfun,
                                                    [depcol], False, "INT")
                table.add_column(newcol)
        # 2. build table queries
        tabqueries = []
        for j, te, table in zip(itertools.count(1), joinentries, tabs):
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
        for i in range(len(joinentries)-1):
            first_ki = len(joinentries[i].view_columns) + 1
            first_kj = len(joinentries[i+1].view_columns) + 1
            s = []
            for k in range(len(joinentries[i].key_columns)):
                s.append("__t{}.__c{} = __t{}.__c{}".format(i+1, first_ki+k,
                                                            i+2, first_kj+k))
            onlines.append("ON " + " AND ".join(s))
        # 4. Build SELECT line
        sellines = []
        # data columns
        for itab in range(len(joinentries)):
            for icol in range(len(joinentries[itab].view_columns)):
                sellines.append("__t{}.__c{}".format(itab+1, icol+1))
        # status columns
        for itab in range(len(joinentries)):
            st = len(joinentries[itab].view_columns)\
                + len(joinentries[itab].key_columns)
            for icol in range(len(joinentries[itab].view_columns)):
                sellines.append("__t{}.__c{}".format(itab+1, st+icol+1))

        selline = "SELECT " + ", ".join(sellines)
        # 5. Assemble origquery
        s = [selline, "FROM", tabqueries[0]]
        for i in range(len(joinentries)-1):
            s.extend(["INNER JOIN", tabqueries[i+1], onlines[i]])
        origquery = "\n".join(s)

        # 6. insert
        _insert_query(self, origquery)

        # 7. remove comparison columns
        for table in tabs:
            for i, kcol in zip(itertools.count(1), te.key_columns):
                col = table.columns["__k{}".format(i)]
                table.remove_column(col)

    return dtab.DataTable(tab_name, proj, init_columns, fill_ttab, False)


def explicit_table(tab_name, colformats, tab, proj):
    """ Assembles a table from given python data.
        colformats = [(name, dt_type, dict), ...]
        tab[][] - table in python types format. None for NULL.

        !!! This procedure modifies tab (converts string values to format
        values). Use deepcopy in order to keep tab unchanged.
    """
    for i, t in enumerate(tab):
        t.insert(0, i+1)

    def init_columns(self):
        self.columns = collections.OrderedDict()
        self.columns['id'] = bcol.build_id()
        for name, dt_type, dict_name in colformats:
            col = bcol.explicit_build(self.proj, name, dt_type, dict_name)
            self.columns[name] = col

    def fill_ttab(self):
        cols, sqlcols = [], []
        for c in self.columns.values():
            cols.append(c)
            sqlcols.append(c.sql_line())

        for i in range(len(tab)):
            for j in range(len(tab[i])):
                tab[i][j] = cols[j].from_repr(tab[i][j])

        pholders = ','.join(['?'] * (len(self.columns)))
        qr = 'INSERT INTO "{tabname}" ({collist}) VALUES ({ph})'.format(
                tabname=self.ttab_name,
                collist=", ".join(sqlcols),
                ph=pholders)
        self.query(qr, tab)

    return dtab.DataTable(tab_name, proj, init_columns, fill_ttab, False)
