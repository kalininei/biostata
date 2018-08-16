import collections


class Signal:
    def __init__(self):
        self._subscribers = []

    def add_subscriber(self, fun):
        self._subscribers.append(fun)

    def remove_subscriver(self, fun):
        self._subscribers.remove(fun)

    def emit(self):
        for s in self._subscribers:
            s()


class DataTable(object):
    def __init__(self, name, proj):
        self.proj = proj
        # =========== data declaration
        # sql data
        self.connection = proj.connection
        self.cursor = self.connection.cursor()
        self.otab_name = name
        # sql data table name: containes tabname data and
        # additional rows representing status of each entry
        self.ttab_name = '_' + name + '_tmp'

        # table data on python side: fetched data which should be shown.
        self.tab = ViewedData(self)

        # columns information
        # original and user defined columns
        self.columns = collections.OrderedDict()
        # _status_columns
        self.extended_columns = {}
        # columns which are visible for user
        self.visible_columns = []

        # representation options
        self.filters = []
        self.group_by = []
        self.ordering = None

        # signal for data changed
        self.updated = Signal()

        # data initialization
        self._init_columns()  # fills self.columns, self.visible columns
        self._init_ttab()     # create aux sql table for red status info

    def _init_columns(self):
        self.columns = collections.OrderedDict()
        self.extended_columns = collections.OrderedDict()
        self.visible_columns = []
        self.cursor.execute("""
            PRAGMA TABLE_INFO("{}")
            """.format(self.otab_name))
        cid, ccat, cdt = [], [], []
        for v in self.cursor.fetchall():
            nm = v[1]
            if nm == 'id':
                col = ColumnInfo.build_id_category()
                cid.append(col)
            else:
                col = ColumnInfo.build_from_category(
                    self.proj.get_category(nm))
                if col.is_category:
                    ccat.append(col)
                else:
                    cdt.append(col)
        if len(cid) != 1:
            raise Exception("unique id column was not found")

        # sort columns in order: id->categories->real data
        for c in cid + ccat + cdt:
            self.columns[c.name] = c
            self.visible_columns.append(c)
            self.extended_columns[c.name] = c.build_status_column()

    def _init_ttab(self):
        collist = []
        for c in self.columns.values():
            if c.name != 'id':
                collist.append("{} {}".format(c.sql_fun, c.sql_data_type))
            else:
                collist.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
            collist.append("{} INTEGER DEFAULT 0".format(
                self.extended_columns[c.name].sql_fun))

        qr = """
        CREATE TEMPORARY TABLE "{0}" ({1})
        """.format(self.ttab_name, ', '.join(collist))
        self.cursor.execute(qr)

        qr = 'INSERT INTO "{0}" ({1}) SELECT {1} from "{2}"'.format(
            self.ttab_name,
            ", ".join([x.sql_fun for x in self.columns.values()]),
            self.otab_name)
        self.cursor.execute(qr)

    def _output_columns_list(self, use_groups):
        vc = len(self.visible_columns)
        ret = []
        # viewed columns
        for c in self.visible_columns:
            ret.append(c.sql_fun)
        # status columns
        for c in self.visible_columns:
            ret.append(self.extended_columns[c.name].sql_fun)

        if use_groups:
            # change property name to its specific function
            for i in range(vc):
                nm = self.visible_columns[i].name
                ret[i] = self.columns[nm].sql_group_fun
                ret[i + vc] = self.extended_columns[nm].sql_group_fun
            # add distinct counts from categories data
            for v in self.visible_columns:
                if v.is_category:
                    ret.append('COUNT(DISTINCT {})'.format(v.sql_fun))
            # add total group length and resulting id column
            ret.append("MIN(id)")
            ret.append("COUNT(id)")

        return ', '.join(ret)

    def _grouping_ordering(self, group):
        if self.ordering:
            oc = self.columns[self.ordering[0]]
        if group:
            gc = [self.columns[x] for x in group]
            grlist = 'GROUP BY ' + ', '.join([x.sql_fun for x in gc])
            order = ['MIN(id) ASC']
            if self.ordering:
                if not oc.is_category:
                    a = oc.sql_group_fun
                    order.insert(0, '{} {}'.format(a, self.ordering[1]))
                elif self.ordering[1] == 'ASC':
                    order.insert(0, 'MIN({}) ASC'.format(oc.sql_fun))
                else:
                    order.insert(0, 'MAX({}) DESC'.format(oc.sql_fun))
            order = 'ORDER BY ' + ', '.join(order)
        else:
            grlist = ''
            if self.ordering:
                order = 'ORDER BY {} {}, id ASC'.format(
                        oc.sql_fun, self.ordering[1])
            else:
                order = 'ORDER BY id ASC'

        return grlist, order

    def _compile_query(self, filters, group):
        # filtration
        fltline = FilterByValue.nested_select(filters)

        # grouping
        grlist, order = self._grouping_ordering(group)

        # get result
        qr = """ SELECT {} FROM "{}" {} {} {} """.format(
            self._output_columns_list(bool(group)),
            self.ttab_name,
            fltline,
            grlist,
            order)
        print(qr)
        return qr

    def update(self):
        qr = self._compile_query(self.filters, self.group_by)
        self.cursor.execute(qr)
        self.tab.fill(self.cursor.fetchall())
        self.updated.emit()

    # ------------------------ Data modification procedures
    def set_data_group_function(self, method):
        if method == 'amean':
            m = "AVG"
        elif method == 'max':
            m = "MAX"
        elif method == 'min':
            m = "MIN"
        elif method == 'median':
            m = "median"
        elif method == 'median+':
            m = "medianp"
        elif method == 'median-':
            m = "medianm"
        else:
            raise NotImplementedError
        for c in self.columns.values():
            if not c.is_category:
                c.sql_group_fun = '{}("{}")'.format(m, c.name)

    # ------------------------ Data access procedures
    def table_name(self):
        return self.otab_name

    def column_role(self, icol):
        """ I - id, C - Category, D - Data """
        if icol == 0:
            return 'I'
        elif self.visible_columns[icol].is_category:
            return 'C'
        else:
            return 'D'

    def column_caption(self, icol):
        return self.visible_columns[icol].short_caption()

    def get_categories(self):
        """ -> [ColumnInfo] (excluding id)"""
        f = lambda x: x.is_category and x.is_original
        return list(filter(f, self.columns.values()))[1:]

    def get_category_names(self):
        """ -> [str category.name] (excluding id)"""
        return [x.name for x in self.get_categories()]

    def get_value(self, r, c):
        col = self.visible_columns[c]
        v = self.tab.get_value(r, c)
        return col.repr(v) if v is not None else None

    def get_subvalues(self, r, c):
        vals = self.tab.get_subvalues(r, c)
        col = self.visible_columns[c]
        return [col.repr(x) if x is not None else None for x in vals]

    def row_definition(self, r):
        """ dictionary which uniquely defines the row (including grouping) """
        return self.tab.rows[r].definition

    def n_cols(self):
        return len(self.visible_columns)

    def n_rows(self):
        try:
            return self.tab.n_rows()
        except:
            return 0

    def n_subrows(self, ir):
        return self.tab.rows[ir].n_sub_values

    def n_subdata_unique(self, ir, ic):
        return self.tab.rows[ir].n_unique_sub_values[ic]

    def n_categories(self):
        ret = 0
        for c in self.visible_columns[1:]:
            if not c.is_category:
                break
            ret += 1
        return ret

    def n_filters(self):
        return len(self.filters)


# =================================== Additional classes
# ------------ Filtration
class FilterByValue(object):
    def __init__(self, nm, val, do_remove, use_and=True):
        leave = "NOT " if do_remove else ""
        if not isinstance(val, collections.Iterable):
            s = '{0} "{1}"={2}'
            self.q = s.format(leave, nm, val)
        else:
            s = []
            for i, j in zip(nm, val):
                s.append('"{0}"={1}'.format(i, j))
            if len(s) == 0:
                self.q = ""
            else:
                cnc = ' AND ' if use_and else ' OR '
                self.q = "{0}({1})".format(leave, cnc.join(s))

    @classmethod
    def nested_select(cls, filterlist):
        flt = list(filter(lambda x: isinstance(x, FilterByValue) and x.q,
                          filterlist))
        if not flt:
            return ""
        else:
            return "WHERE " +\
                ' AND '.join([x.q for x in flt])


# -------------------- Column information
class ColumnInfo:
    def __init__(self):
        self.name = None
        self.longname = None
        self.is_original = None
        self.is_category = None
        self.dt_type = None
        self.sql_group_fun = None
        self.sql_fun = None
        self.sql_data_type = None
        self.__long_caption = None
        # this is not none only for enum and boolean types
        self.possible_values = None
        self.possible_values_short = None
        # defined delegates
        self.repr = lambda x: x
        self.from_repr = lambda x: x

    @classmethod
    def build_from_category(cls, category):
        ret = cls()
        ret.name = category.name
        ret.shortname = category.shortname
        ret.is_original = True
        ret.is_category = category.is_category
        if ret.is_category:
            ret.sql_group_fun = 'category_group("{}")'.format(ret.name)
        else:
            ret.sql_group_fun = 'AVG("{}")'.format(ret.name)
        ret.sql_fun = '"' + ret.name + '"'
        ret.dt_type = category.dt_type
        if category.dt_type != "REAL":
            ret.sql_data_type = "INTEGER"
        else:
            ret.sql_data_type = "REAL"
        if category.dim:
            ret.__long_caption = "{}, {}".format(ret.name, category.dim)
        else:
            ret.__long_caption = ret.name

        ret.possible_values = category.possible_values
        ret.possible_values_short = category.possible_values_short

        # changing representation function for boolean and enum types
        if category.dt_type == "ENUM":
            ret.repr = lambda x: ret.possible_values_short[x]
            ret.from_repr = lambda x: next(
                k for k, v in ret.possible_values_short.items() if v == x)
        if category.dt_type == "BOOLEAN":
            ret.repr = lambda x: bool(x)
            ret.from_repr = lambda x: 1 if x else 0

        return ret

    @classmethod
    def build_id_category(cls):
        ret = cls()
        ret.name = 'id'
        ret.shortname = 'id'
        ret.is_original = True
        ret.is_category = True
        ret.dt_type = "INTEGER"
        ret.sql_group_fun = 'category_group(id)'
        ret.sql_fun = "id"
        ret.sql_data_type = "INTEGER"
        ret.__long_caption = "id"
        return ret

    def build_status_column(self):
        ret = ColumnInfo()
        ret.name = '_status_' + self.name
        ret.is_original = False
        ret.is_category = True
        ret.dt_type = "BOOLEAN"
        ret.sql_group_fun = 'MAX("{}")'.format(ret.name)
        ret.sql_fun = '"{}"'.format(ret.name)
        ret.sql_data_type = "INTEGER"
        return ret

    def short_caption(self):
        return self.shortname

    def long_caption(self):
        return self.__long_caption


# ------------ Visible table
class ViewedData:
    class Row:
        def __init__(self, inp, model):
            self.model = model
            vc = len(model.visible_columns)
            self.values = list(inp[:vc])
            self.id = self.values[0]
            self.status = list(inp[vc:2*vc])
            self.sub_values_requested = False
            self.sub_values = self.sub_status = [[] for _ in range(vc)]
            self.n_unique_sub_values = [1] * vc
            if model.group_by:
                self.n_sub_values = inp[-1]
                self.id = inp[-2]
                for i in range(vc):
                    if model.visible_columns[i].is_category:
                        self.n_unique_sub_values[i] = inp[2*vc+i]
                    else:
                        self.n_unique_sub_values[i] = inp[-1]
            else:
                self.n_sub_values = 0
            self.definition = self._row_def()

        def value_by_name(self, nm):
            for index, c in enumerate(self.model.visible_columns):
                if c.name == nm:
                    return self.values[index]
            raise KeyError

        def subvalues(self, j):
            if not self.sub_values_requested:
                self._request_subvalues()
            return [x[j] for x in self.sub_values]

        def substatus(self, j):
            if not self.sub_values_requested:
                self._request_subvalues()
            return [x[j] for x in self.sub_status]

        def _row_def(self):
            """ -> {field: value}, unique for this row """
            if not self.model.group_by:
                return {"id": self.values[0]}
            else:
                ret = {}
                for n in self.model.group_by:
                    try:
                        ret[n] = self.value_by_name(n)
                    except KeyError:
                        # grouped value does not present in the data
                        # hence we make a query through the id
                        qr = 'SELECT {} from "{}" WHERE id={}'.format(
                            n, self.model.ttab_name, self.id)
                        self.model.cursor.execute(qr)
                        ret[n] = self.model.cursor.fetchone()[0]
                return ret

        def _request_subvalues(self):
            if self.n_sub_values == 1:
                self.sub_values = [self.values]
                self.sub_status = [self.status]
            else:
                vc = len(self.model.visible_columns)
                # add additional filters defining this group
                flt = self.model.filters[:]
                flt.append(FilterByValue(
                    self.definition.keys(), self.definition.values(),
                    False, True))
                # build query
                qr = self.model._compile_query(flt, [])
                self.model.cursor.execute(qr)
                # fill data
                f = self.model.cursor.fetchall()
                self.sub_values = [list(x[:vc]) for x in f]
                self.sub_status = [list(x[vc:2*vc]) for x in f]

            self.sub_values_requested = True

    def __init__(self, model):
        self.model = model
        self.rows = []

    def n_rows(self):
        return len(self.rows)

    def fill(self, inp):
        self.rows.clear()
        for x in inp:
            self.rows.append(ViewedData.Row(x, self.model))

    def get_value(self, i, j):
        return self.rows[i].values[j]

    def get_status(self, i, j):
        return self.rows[i].status[j]

    def get_subvalues(self, i, j):
        return self.rows[i].subvalues(j)

    def get_substatus(self, i, j):
        return self.rows[i].substatus(j)
