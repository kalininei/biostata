import itertools
import collections
from bdata import filt
from bdata import bcol
from bdata import bsqlproc


class DataTable(object):
    """ this class contains
        modification options of a given table
        with the results of these modification (self.tab)
    """
    def __init__(self, name, proj):
        self.proj = proj
        # =========== data declaration
        # sql data
        self.connection = proj.connection
        self.cursor = self.connection.cursor()
        self.name = name
        # sql data table name: containes tabname data and
        # additional rows representing status of each entry
        self.ttab_name = '_' + name + '_tmp'

        # columns information
        # original and user defined columns
        self.columns = collections.OrderedDict()
        # self columns in order they should be viewed
        self.all_columns = []
        # columns which are visible for user
        self.visible_columns = []

        # method for data grouping
        self._default_group_method = "AVG"

        # representation options
        self.group_by = []
        self.ordering = None

        # filters: anon filters belong to current tables,
        #          named filters are taked from self.proj.
        #          used_filters contain both anon and named filters
        self.all_anon_filters = []
        self.used_filters = []

        # table data on python side: fetched data which should be shown.
        self.tab = ViewedData(self)

        # data initialization
        self._init_columns()  # fills self.columns, self.visible columns
        self._assemble_ttab()     # create aux sql table for red status info

    def destruct(self):
        qr = 'DROP TABLE "{}"'.format(self.ttab_name)
        self.query(qr)

    def _assemble_ttab(self):
        self._create_ttab()
        self._fill_ttab()

    def _create_ttab(self):
        collist = []
        for c in self.columns.values():
            if c.name != 'id':
                collist.append("{} {}".format(c.sql_fun, c.sql_data_type))
            else:
                collist.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
            if c.is_original:
                collist.append("{} INTEGER DEFAULT 0".format(
                    self.columns[c.name].status_column.sql_fun))

        qr = """CREATE TEMPORARY TABLE "{0}" ({1})
        """.format(self.ttab_name, ', '.join(collist))
        self.query(qr)

    def _fill_ttab(self):
        raise NotImplementedError

    def _init_columns(self):
        raise NotImplementedError

    def is_original(self):
        return False

    def _output_columns_list(self, cols, status_adds, use_groups, group_adds):
        ret = []
        for c in cols:
            # viewed columns
            ret.append(c.sql_fun)
        if status_adds:
            # status columns
            for c in cols:
                ret.append(c.status_column.sql_fun)

        if use_groups:
            # change property name to its specific function
            for i, c in enumerate(cols):
                ret[i] = c.sql_group_fun
            if status_adds:
                for i, c in zip(itertools.count(len(cols)), cols):
                    ret[i] = c.status_column.sql_group_fun
            if group_adds:
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
            try:
                oc = self.columns[self.ordering[0]]
            except KeyError:
                self.ordering = None
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

    def _compile_query(self, cols=None, status_adds=True,
                       filters=None, group=None, group_adds=True):
        if cols is None:
            cols = self.visible_columns
        if filters is None:
            filters = self.used_filters
        if group is None:
            group = self.group_by
        # filtration
        fltline = filt.Filter.compile_sql_line(filters)

        # grouping
        grlist, order = self._grouping_ordering(group)

        collist = self._output_columns_list(cols, status_adds,
                                            bool(group), group_adds)
        # get result
        qr = """ SELECT {} FROM "{}" {} {} {} """.format(
            collist,
            self.ttab_name,
            fltline,
            grlist,
            order)
        return qr

    def query(self, qr):
        print(qr)
        self.cursor.execute(qr)

    def update(self):
        self.query(self._compile_query())
        self.tab.fill(self.cursor.fetchall())

    def merge_categories(self, categories):
        """ Creates new column build of merged list of categories,
               places it after the last visible category column
            categories -- list of ColumnInfo entries
            returns newly created column or
                    None if this column already exists
        """
        if len(categories) < 2:
            return None
        # create column
        col = bcol.CollapsedCategories(categories)
        # check if this merge was already done
        if col.name in self.columns.keys():
            return None
        self.add_column(col)
        # place to the visible columns list
        for i, c in enumerate(self.visible_columns):
            if not c.is_category:
                break
        self.visible_columns.insert(i, col)
        return col

    # ------------------------ Data modification procedures
    def set_data_group_function(self, method=None):
        if method is not None:
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
            self._default_group_method = m
        else:
            m = self._default_group_method
        for c in self.columns.values():
            if not c.is_category:
                c.sql_group_fun = '{}("{}")'.format(m, c.name)

    def remove_column(self, col):
        if col.is_original:
            raise Exception(
                "Can not remove original column {}".format(col.name))
        try:
            self.columns.pop(col.name)
        except:
            pass
        try:
            self.all_columns.remove(col)
        except:
            pass
        try:
            self.visible_columns.remove(col)
        except:
            pass

    def add_column(self, col, pos=None, is_visible=False):
        if col.name not in self.columns:
            self.columns[col.name] = col
            if not col.is_category:
                self.set_data_group_function()
            if pos is None:
                pos = len(self.columns)
        else:
            # if column already presents in current data
            if pos is None:
                pos = self.all_columns.index(col)
            # temporary remove column from lists
            try:
                self.all_columns.remove(col)
            except:
                pass
            try:
                self.visible_columns.remove(col)
            except:
                pass
        # maximum position for category column
        # or minimum for data column
        limpos = 0
        while limpos < len(self.all_columns) and\
                self.all_columns[limpos].is_category:
            limpos += 1
        # add to all_columns
        if col.is_category:
            pos = min(pos, limpos)
        else:
            pos = max(pos, limpos)
        self.all_columns.insert(pos, col)
        # visibles
        vis_set = set(self.visible_columns)
        if is_visible:
            vis_set.add(col)
        self._assemble_visibles(vis_set)

    def set_visibility(self, col, do_show):
        is_visible = col in self.visible_columns
        if is_visible == do_show:
            return
        if not do_show:
            self.visible_columns.remove(col)
        else:
            assert col in self.all_columns
            vis_set = set(self.visible_columns + [col])
            self._assemble_visibles(vis_set)

    def _assemble_visibles(self, vis_set):
        self.visible_columns.clear()
        for c in self.all_columns:
            if c in vis_set:
                self.visible_columns.append(c)

    def add_filter(self, f, use=True):
        if f.name is None:
            if f not in self.all_anon_filters:
                self.all_anon_filters.append(f)
        else:
            if f not in self.proj.named_filters:
                self.proj.named_filters.append(f)
        if use and f not in self.used_filters:
            self.used_filters.append(f)

    def set_filter_usage(self, f, use):
        if not use:
            if f in self.used_filters:
                self.used_filters.remove(f)
        elif use and f not in self.used_filters:
            if f.name and f in self.proj.named_filters:
                self.used_filters.append(f)
            if not f.name and f in self.all_anon_filters:
                self.used_filters.append(f)

    def set_named_filters(self, filtlist):
        self.proj.set_named_filters(filtlist)

    def set_anon_filters(self, filtlist):
        self.all_anon_filters.clear()
        for f in filtlist:
            if f.is_applicable(self):
                self.all_anon_filters.append(f)

    def set_active_filters(self, filtlist):
        self.used_filters.clear()
        for f in filtlist:
            self.set_filter_usage(f, True)

    # ------------------------ info and checks
    def table_name(self):
        return self.name

    def column_role(self, icol):
        """ I - id, C - Category, D - Data """
        if icol == 0:
            return 'I'
        elif self.visible_columns[icol].is_category:
            return 'C'
        else:
            return 'D'

    def column_caption(self, icol):
        return self.visible_columns[icol].long_caption()

    def get_categories(self):
        """ -> [ColumnInfo] (excluding id)"""
        f = lambda x: x.is_category and x.is_original
        return list(filter(f, self.columns.values()))[1:]

    def get_category_names(self):
        """ -> [str category.name] (excluding id)"""
        return [x.name for x in self.get_categories()]

    def n_cols(self):
        return len(self.visible_columns)

    def n_rows(self):
        try:
            return self.tab.n_rows()
        except:
            return 0

    def applicable_named_filters(self):
        return [f for f in self.proj.named_filters if f.is_applicable(self)]

    def n_subrows(self, ir):
        return self.tab.rows[ir].n_sub_values

    def n_subdata_unique(self, ir, ic):
        return self.tab.rows[ir].n_unique_sub_values[ic]

    def n_visible_categories(self):
        ret = 0
        for c in self.visible_columns[1:]:
            if not c.is_category:
                break
            ret += 1
        return ret

    def is_valid_column_name(self, nm, shortnm='valid'):
        """ checks if nm could be used as a new column name for this tab
            raises Exception if negative
        """
        # name
        if not isinstance(nm, str) or not nm.strip():
            raise Exception("Column name should be a valid string")
        if nm[0] == '_':
            raise Exception("Column name should not start with '_'")
        cnames = list(map(lambda x: x.upper(), self.columns.keys()))
        if nm.upper() in cnames:
            raise Exception("Column name already exists in present table")
        for c in ['&', '"', "'"]:
            if nm.find(c) >= 0:
                raise Exception("Column name should not contain "
                                "ampersand or quotes signs")
        # short name
        if not isinstance(shortnm, str) or not shortnm.strip():
            raise Exception("Column short name should be a valid string")
        if shortnm[0] == '_':
            raise Exception("Column short name should not start with '_'")
        for c in ['&', '"', "'"]:
            if shortnm.find(c) >= 0:
                raise Exception("Column short name should not contain "
                                "ampersand or quotes signs")
        return True

    # ------------------------ Data access procedures
    def get_value(self, r, c):
        col = self.visible_columns[c]
        v = self.tab.get_value(r, c)
        return col.repr(v) if v is not None else None

    def get_subvalues(self, r, c):
        vals = self.tab.get_subvalues(r, c)
        col = self.visible_columns[c]
        return [col.repr(x) if x is not None else None for x in vals]

    def get_raw_value(self, r, c):
        return self.tab.get_value(r, c)

    def get_raw_subvalues(self, r, c):
        return self.tab.get_subvalues(r, c)

    def row_definition(self, r):
        """ dictionary which uniquely defines the row (including grouping) """
        return self.tab.rows[r].definition

    def ids_by_row(self, r):
        id0 = self.get_raw_value(r, 0)
        if id0 is not None:
            return [id0]
        else:
            return self.get_raw_subvalues(r, 0)

    def get_raw_minmax(self, cname, is_global=False):
        if cname == 'id' and is_global:
            qr = 'SELECT COUNT(id) FROM "{}"'.format(self.ttab_name)
            self.query(qr)
            return (1, int(self.cursor.fetchone()[0]))
        col = self.columns[cname]
        if is_global:
            qr = 'SELECT MIN({0}), MAX({0}) FROM "{1}"'.format(
                    col.sql_fun, self.ttab_name)
            self.query(qr)
            return self.cursor.fetchall()[0]
        else:
            raise NotImplementedError

    def get_raw_column_values(self, cname):
        try:
            # if cname in visibles no need to make a query
            ind = [x.name for x in self.visible_columns].index(cname)
            return self.tab.get_column_values(ind)
        except ValueError:
            qr = self._compile_query([self.columns[cname]], False)
            self.query(qr)
            return [x[0] for x in self.cursor.fetchall()]

    def get_distinct_column_raw_vals(self, cname):
        """ -> distinct vals in global scope (ignores filters, groups etc)
        """
        col = self.columns[cname]
        qr = 'SELECT DISTINCT({0}) FROM "{1}"'.format(
                col.sql_fun, self.ttab_name)
        self.query(qr)
        return [x[0] for x in self.cursor.fetchall()]


class OriginalTable(DataTable):
    """ table built from database table """
    def __init__(self, tab_name, proj):
        super().__init__(tab_name, proj)

    def is_original(self):
        return True

    def _init_columns(self):
        self.columns = collections.OrderedDict()
        self.all_columns = []
        self.visible_columns = []
        self.query("""PRAGMA TABLE_INFO("{}")""".format(self.name))
        cid, ccat, cdt = [], [], []
        for v in self.cursor.fetchall():
            nm = v[1]
            if nm == 'id':
                col = bcol.ColumnInfo.build_id_category()
                cid.append(col)
            else:
                col = bcol.ColumnInfo.build_from_category(
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
            self.all_columns.append(c)

    def _fill_ttab(self):
        qr = 'INSERT INTO "{0}" ({1}) SELECT {1} from "{2}"'.format(
            self.ttab_name,
            ", ".join([x.sql_fun for x in self.columns.values()]),
            self.name)
        self.query(qr)


class DerivedTable(DataTable):
    """ Table derived from a set of other tables """
    def __init__(self, name, origtables, proj):
        self.dependencies = origtables
        super().__init__(name, proj)


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
        self.columns['id'] = bcol.ColumnInfo.build_id_category()
        for k, v in zip(self._given_cols_names, self._given_cols_list):
            try:
                self.columns[k] = v.build_deep_copy(k)
            except bcol.CollapsedCategories.InvalidDeepCopy:
                # we cannot make a deep copy of a collapsed column
                # so we convert it to ENUM type
                dv = self.dependencies[0].get_raw_column_values(v.name)
                dv2 = sorted(set(dv))
                col = bcol.ColumnInfo.build_enum_category(k, v.shortname, dv2)
                self.columns[k] = col

        self.all_columns = []
        self.visible_columns = []
        for v in self.columns.values():
            self.all_columns.append(v)
            self.visible_columns.append(v)

    def _fill_ttab(self):
        # here we substitude sql codes for merged columns to
        # convert them to enums
        _bu = []
        for (txtcol, nm) in zip(self._given_cols_list, self._given_cols_names):
            if isinstance(txtcol, bcol.CollapsedCategories):
                dfun = bsqlproc.build_txt_to_enum(
                        self.columns[nm].possible_values, self.connection)
                _bu.append(txtcol.sql_fun)
                _bu.append(txtcol.sql_group_fun)
                txtcol.sql_fun = "{}({})".format(dfun, txtcol.sql_fun)
                txtcol.sql_group_fun = "{}({})".format(
                        dfun, txtcol.sql_group_fun)

        # build a query to the original table
        origquery = self.dependencies[0]._compile_query(
                cols=self._given_cols_list,
                status_adds=True,
                group_adds=False)

        # place sql codes for merged columns back
        # modify resulting column dictinary: 1 -> '1 & 2' -> 'code1-code2'
        it = iter(_bu)
        for (txtcol, nm) in zip(self._given_cols_list, self._given_cols_names):
            if isinstance(txtcol, bcol.CollapsedCategories):
                txtcol.sql_fun = next(it)
                txtcol.sql_group_fun = next(it)
                for k, v in self.columns[nm].possible_values.items():
                    self.columns[nm].possible_values[k] = txtcol.repr(v)

        # insert query
        sqlcols, sqlcols2 = [], []
        for c in itertools.islice(self.columns.values(), 1, None):
            sqlcols.append(c.sql_fun)
            sqlcols2.append(c.status_column.sql_fun)
        qr = 'INSERT INTO "{tabname}" ({collist}) {select_from_orig}'.format(
                tabname=self.ttab_name,
                collist=", ".join(itertools.chain(sqlcols, sqlcols2)),
                select_from_orig=origquery)
        self.query(qr)


# =================================== Additional classes
# ------------ Visible table
class ViewedData:
    class Row:
        def __init__(self, inp, model):
            self.model = model
            vc = len(model.visible_columns)
            self.values = inp[:vc]
            self.status = inp[vc:2*vc]
            self.id = self.values[0]
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
                            self.model.columns[n].sql_fun,
                            self.model.ttab_name,
                            self.id)
                        self.model.query(qr)
                        ret[n] = self.model.cursor.fetchone()[0]
                return ret

        def _request_subvalues(self):
            if self.n_sub_values == 1:
                self.sub_values = [self.values]
                self.sub_status = [self.status]
            else:
                vc = len(self.model.visible_columns)
                # add additional filters defining this group
                flt = self.model.used_filters[:]
                flt.append(filt.Filter.filter_by_values(
                        self.model, self.definition.keys(),
                        self.definition.values(), False, True))
                # build query
                qr = self.model._compile_query(filters=flt, group=[])
                self.model.query(qr)
                # fill data
                f = self.model.cursor.fetchall()
                self.sub_values = [x[:vc] for x in f]
                self.sub_status = [x[vc:2*vc] for x in f]

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

    def get_column_values(self, j):
        return [self.rows[i].values[j] for i in range(self.n_rows())]
