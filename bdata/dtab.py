import collections
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, unescape
from bdata import filt
from bdata import bcol
from prog import basic


class DataTable(object):
    """ this class contains
        modification options of a given table
        with the results of these modification (self.tab)
    """
    def __init__(self, name, proj,
                 init_columns, fill_ttab, isorig):
        """
        init_columns:def(DataTable) - delegate for self.columns initialization
        fill_ttab:def(DataTable) - delegate that fills temporary table
                                   self.ttab_name
        isorig:bool - do we have table named self.name in the database
        """
        self.proj = proj
        self.comment = None
        self._isorig = isorig
        self.need_rewrite = not isorig
        # =========== data declaration
        # sql data
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
        init_columns(self)   # fills self.columns, self.visible columns
        self._create_ttab()  # create temporary sql table
        fill_ttab(self)      # ... and fills it

        # reorders columns (categorical->real),
        # fills all columns, visible columns
        self._complete_columns_lists()

    def _create_ttab(self):
        collist = []
        for c in filter(lambda x: x.is_original(), self.columns.values()):
            if c.name != 'id':
                collist.append("{} {}".format(c.sql_line(False),
                                              c.sql_data_type()))
            else:
                collist.append("id INTEGER UNIQUE")
            collist.append("{} INTEGER DEFAULT 0".format(
                self.columns[c.name].status_column.sql_line(False)))

        self.query('DROP TABLE IF EXISTS "{}"'.format(self.ttab_name))
        qr = """CREATE TABLE "{0}" ({1})
        """.format(self.ttab_name, ', '.join(collist))
        self.query(qr)

    def _complete_columns_lists(self):
        self.all_columns = []
        self.visible_columns = []
        for v in filter(lambda x: x.is_category(), self.columns.values()):
            self.all_columns.append(v)
            self.visible_columns.append(v)
        for v in filter(lambda x: not x.is_category(), self.columns.values()):
            self.all_columns.append(v)
            self.visible_columns.append(v)
        self.columns.clear()
        for c in self.all_columns:
            self.columns[c.name] = c

    @staticmethod
    def _fix_column_order(lst):
        c1 = list(filter(lambda x: x.is_category(), lst))
        c2 = list(filter(lambda x: not x.is_category(), lst))
        lst.clear()
        lst.extend(c1)
        lst.extend(c2)

    def is_original(self):
        return self._isorig

    # ================ database manipulations (called only from self.proj)
    def destruct(self):
        """ removes temporary tables only """
        qr = 'DROP TABLE "{}"'.format(self.ttab_name)
        self.query(qr)

    def to_original(self):
        """ creates a table named "self.name" and writes there all data from
            temporary table
        """
        if self.is_original():
            return
        self._isorig = True
        self.set_need_rewrite(True)

    def set_need_rewrite(self, need):
        """ Do we need to write this table to the original database
            in the next commit event
        """
        self.need_rewrite = need

    def write_to_db(self):
        ' flushes current data to A database if needed '
        if not self.is_original() or not self.need_rewrite:
            return
        self.query('DROP TABLE IF EXISTS A."{}"'.format(self.name))
        colstring = [('id', 'INTEGER UNIQUE')]
        for c in filter(lambda x: x.is_original(), self.all_columns[1:]):
            colstring.append((c.name, c.sql_data_type()))
        colstring1 = ', '.join(['"{}" {}'.format(x[0], x[1])
                               for x in colstring])
        colstring2 = ', '.join(['"{}"'.format(x[0]) for x in colstring])
        qr = 'CREATE TABLE A."{}" ({})'.format(self.name, colstring1)
        self.query(qr)
        qr = 'INSERT INTO A."{0}" ({1}) SELECT {1} from "{2}"'.format(
            self.name, colstring2, self.ttab_name)
        self.query(qr)
        self.set_need_rewrite(False)

    # ================== SQL query procedures
    def _output_columns_list(self, cols, status_adds=False, use_groups=None,
                             group_adds=False, auto_alias=""):
        if use_groups is None:
            use_groups = bool(self.group_by)
        ret = []
        for c in cols:
            # viewed columns
            ret.append(c.sql_line(use_groups))
        if status_adds:
            # status columns
            for c in cols:
                ret.append(c.status_column.sql_line(use_groups))

        if use_groups and group_adds:
            # add distinct counts from categories data
            for v in self.visible_columns:
                if v.is_category():
                    ret.append('COUNT(DISTINCT {})'.format(v.sql_line()))
            # add total group length and resulting id column
            ret.append("MIN(id)")
            ret.append("COUNT(id)")

        if auto_alias:
            for i in range(len(ret)):
                ret[i] = ret[i] + ' AS {}{}'.format(auto_alias, i+1)

        return ', '.join(ret)

    def _grouping_ordering(self, group):
        if self.ordering:
            try:
                oc = self.columns[self.ordering[0]]
            except KeyError:
                self.ordering = None
        if group:
            gc = [self.columns[x] for x in group]
            grlist = 'GROUP BY ' + ', '.join([x.sql_line() for x in gc])
            order = ['MIN(id) ASC']
            if self.ordering:
                if not oc.is_category():
                    order.insert(0, '{} {}'.format(oc.sql_line(True),
                                                   self.ordering[1]))
                elif self.ordering[1] == 'ASC':
                    order.insert(0, 'MIN({}) ASC'.format(oc.sql_line()))
                else:
                    order.insert(0, 'MAX({}) DESC'.format(oc.sql_line()))
            order = 'ORDER BY ' + ', '.join(order)
        else:
            grlist = ''
            if self.ordering:
                order = 'ORDER BY {} {}, id ASC'.format(
                        oc.sql_line(), self.ordering[1])
            else:
                order = 'ORDER BY id ASC'

        return grlist, order

    def _compile_query(self, cols=None, status_adds=True,
                       filters=None, group=None, group_adds=True,
                       auto_alias=""):
        """ cols([ColumnInfo]) -- list of columns to be included,
                    if None -> all visible columns
            status_adds -- whether to add status columns to query
            filters([Filter]) -- list of filters. If none -> all used_fileters
            group([col names]) -- list of column names at which to provide
                    grouping. If none => self.group_by
            group_adds -- whether to add grouping info column like COUNT etc.
            auto_alias(str) --  adds "AS ...{1,2,3}" to each column
        """
        if cols is None:
            cols = self.visible_columns
        if filters is None:
            filters = self.used_filters
        if group is None:
            group = self.group_by
        # filtration
        fltline = filt.Filter.compile_sql_line(filters, self)

        # grouping
        grlist, order = self._grouping_ordering(group)

        collist = self._output_columns_list(cols, status_adds,
                                            bool(group), group_adds,
                                            auto_alias)
        # get result
        qr = """SELECT {} FROM "{}" {} {} {}""".format(
            collist,
            self.ttab_name,
            fltline,
            grlist,
            order)
        return qr

    def query(self, qr, dt=None):
        self.proj.sql.query(qr, dt)

    def qresult(self):
        return self.proj.sql.qresult()

    def qresults(self):
        return self.proj.sql.qresults()

    def update(self):
        self.query(self._compile_query())
        self.tab.fill(self.qresults())

    # ------------------------ Data modification procedures
    def merge_categories(self, categories, delim):
        """ Creates new column build of merged list of categories,
               places it after the last visible category column
            categories -- list of ColumnInfo entries
            returns newly created column or
                    None if this column already exists
        """
        if len(categories) < 2:
            return None
        # create column
        col = bcol.collapsed_categories(categories, delim)
        # check if this merge was already done
        if col.name in self.columns.keys():
            return None
        self.add_column(col)
        # place to the visible columns list
        for i, c in enumerate(self.visible_columns):
            if not c.is_category():
                break
        self.visible_columns.insert(i, col)
        return col

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
            c.real_data_groupfun = m

    def remove_column(self, col):
        if col.is_original():
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
            if not col.is_category():
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
                self.all_columns[limpos].is_category():
            limpos += 1
        # add to all_columns
        if col.is_category():
            pos = min(pos, limpos)
        else:
            pos = max(pos, limpos)
        self.all_columns.insert(pos, col)
        # visibles
        vis_set = set(self.visible_columns)
        if is_visible:
            vis_set.add(col)
        self._assemble_visibles(vis_set)

        if col.is_original():
            self.set_need_rewrite(True)

    def convert_column(self, cname, newtype, dct=None):
        """ converts given column to a given newtype
        """
        col = self.columns[cname]
        if col.dt_type in ['BOOL', 'ENUM'] and newtype == 'INT':
            col.set_repr_delegate(bcol.IntRepr())
        elif col.dt_type == 'INT' and newtype == 'BOOL':
            col.set_repr_delegate(bcol.BoolRepr(dct))
        elif col.dt_type == 'INT' and newtype == 'ENUM':
            col.set_repr_delegate(bcol.EnumRepr(dct))
        else:
            raise NotImplementedError

    def remove_entries(self, flt):
        """ Removes entries according to a given filter,
            retruns number of removed lines.
        """
        qr = 'DELETE FROM "{}" WHERE ({})'.format(
            self.ttab_name, flt.to_sqlline())
        self.query(qr)
        self.query("SELECT CHANGES()")
        ret = self.qresult()[0]
        if ret > 0:
            self.reset_id()
        return ret

    def reset_id(self):
        """ Fills id column with 1, 2, 3, ... values.
            Does not check if id values are already in correct order.
            Set need_rewrite to true.
        """
        self.query('SELECT COUNT(id) from "{}"'.format(self.ttab_name))
        nums = range(1, self.qresult()[0] + 1)
        # update filters that use id
        idfilters = list(filter(lambda x: isinstance(x, filt.IdFilter),
                                self.all_anon_filters))
        if len(idfilters) > 0:
            self.query('SELECT id FROM "{}" ORDER BY id'.format(
                self.ttab_name))
            old_id = [x[0] for x in self.qresults()]
            for f in idfilters:
                if not f.reset_id(old_id):
                    self.all_anon_filters.remove(f)
        # update id column
        self.query('UPDATE "{}" SET id = ?', ((x,) for x in nums))
        self.set_need_rewrite(True)

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
    def current_state_xml(self):
        root = ET.Element('TableState')
        # ---- columns
        cur = ET.SubElement(root, "COLUMNS")
        # all columns
        ET.SubElement(cur, "ALL_COLUMNS").text =\
            escape(str([x.name for x in self.all_columns]))
        # visible columns
        ET.SubElement(cur, "VISIBLE_COLUMNS").text =\
            escape(str([x.name for x in self.visible_columns]))
        # ----- filters
        cur = ET.SubElement(root, "FILTERS")
        # anonymous filters
        for i, f in enumerate(self.all_anon_filters):
            n = ET.SubElement(cur, "FILTER")
            f.to_xml(n, "_anon{}".format(i+1))
        # used filter
        uf = []
        for f in self.used_filters:
            nm = f.name
            if nm is None:
                i = self.all_anon_filters.index(f)
                nm = "_anon{}".format(i+1)
            uf.append(nm)
        ET.SubElement(cur, "USED_FILTERS").text = escape(str(uf))
        # ----- ordering
        ET.SubElement(root, "ORDER_BY").text = escape(str(self.ordering))

        # ----- grouping
        ET.SubElement(root, "GROUP_BY").text = escape(str(self.group_by))

        # ----- return
        return ET.tostring(root, encoding='utf-8', method='xml').decode()

    def restore_state_by_xml(self, string):
        from ast import literal_eval
        root = ET.fromstring(string)
        # all columns
        try:
            line = unescape(root.find('COLUMNS/ALL_COLUMNS').text)
            line = literal_eval(line)
            cols = [self.columns[x] for x in line if x in self.columns]
            cols.extend(filter(lambda x: x not in cols, self.all_columns))
            self._fix_column_order(cols)
        except Exception as e:
            basic.ignore_exception(e)
        else:
            self.all_columns = cols
        # visible columns
        try:
            line = unescape(root.find('COLUMNS/VISIBLE_COLUMNS').text)
            line = literal_eval(line)
            cols = [self.columns[x] for x in line if x in self.columns]
            self._fix_column_order(cols)
        except Exception as e:
            basic.ignore_exception(e)
        else:
            self.visible_columns = cols
        # filters
        try:
            anons, usedf = [], []
            # anonymous filters
            for nd in root.findall('FILTERS/FILTER'):
                anons.append(filt.Filter.from_xml(nd))
            for a in anons:
                a.name = None
            # used filters
            line = literal_eval(unescape(root.find(
                'FILTERS/USED_FILTERS').text))
            for nm in line:
                if nm[:5] == '_anon':
                    anon_i = int(nm[5:]) - 1
                    if anon_i < len(anons):
                        usedf.append(anons[anon_i])
                else:
                    usedf.append(self.proj.get_named_filter(nm))
        except Exception as e:
            basic.ignore_exception(e)
        else:
            self.all_anon_filters = anons
            self.used_filters = usedf
        # ordering
        try:
            nord = literal_eval(unescape(root.find('ORDER_BY').text))
            if nord is not None and nord[0] not in self.columns:
                raise Exception("invalid order column name")
        except Exception as e:
            basic.ignore_exception(e)
        else:
            self.ordering = nord
        # grouping
        try:
            ngr = literal_eval(unescape(root.find('GROUP_BY').text))
            for g in ngr:
                if g not in self.columns:
                    raise Exception("invalid group column name")
        except Exception as e:
            basic.ignore_exception(e)
        else:
            self.group_by = ngr

    def table_name(self):
        return self.name

    def column_role(self, icol):
        """ I - id, C - Category, D - Data """
        if icol == 0:
            return 'I'
        elif self.visible_columns[icol].is_category():
            return 'C'
        else:
            return 'D'

    def column_caption(self, icol):
        return self.visible_columns[icol].name

    def get_categories(self):
        """ -> [ColumnInfo] (excluding id)"""
        return list(filter(lambda x: x.is_category(),
                           self.columns.values()))[1:]

    def column_dependencies(self, colname):
        ret = set([colname])
        col = self.column[colname]
        for c in filter(lambda x: isinstance(x, bcol.DerivedColumnInfo)):
            if col in c.dependencies:
                ret.intersection_update(
                        self.column_dependencies(c.name))
        return ret

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
            if not c.is_category():
                break
            ret += 1
        return ret

    def is_valid_column_name(self, nm, shortnm='valid'):
        """ checks if nm could be used as a new column name for this tab
            raises Exception if negative
        """
        # name
        self.proj.is_possible_column_name(nm)
        cnames = list(map(lambda x: x.upper(), self.columns.keys()))
        if nm.upper() in cnames:
            raise Exception(
                'Column name "{}" already exists in the table'.format(nm))
        # short name
        if shortnm != 'valid':
            self.proj.is_possible_column_name(shortnm)
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
            return (1, int(self.qresult()[0]))
        col = self.columns[cname]
        if is_global:
            qr = 'SELECT MIN({0}), MAX({0}) FROM "{1}"'.format(
                    col.sql_line(), self.ttab_name)
            self.query(qr)
            return self.qresults()[0]
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
            return [x[0] for x in self.qresults()]

    def get_distinct_column_raw_vals(self, cname, is_global=True):
        """ -> distinct vals in global scope (ignores filters, groups etc)
               or local scope (including all settings)
        """
        col = self.columns[cname]
        if is_global:
            qr = 'SELECT DISTINCT({0}) FROM "{1}"'.format(
                    col.sql_line(), self.ttab_name)
        else:
            qr = self._compile_query([col], status_adds=False,
                                     group_adds=False)
            qr = qr.replace("SELECT", "SELECT DISTINCT", 1)
        self.query(qr)
        return [x[0] for x in self.qresults()]

    def redstatus_bytearray(self, colname):
        """ returns bytearray of column redstatuses if there are
            any positive values, else returns None
        """
        col = self.columns[colname]
        if not col.is_original():
            return None
        nm = col.status_column.sql_line()
        qr = 'SELECT COUNT(DISTINCT {}) from "{}"'.format(nm, self.ttab_name)
        self.query(qr)
        if self.qresult()[0] <= 1:
            return None
        else:
            raise NotImplementedError


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
                    if model.visible_columns[i].is_category():
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
                            self.model.columns[n].sql_line(),
                            self.model.ttab_name,
                            self.id)
                        self.model.query(qr)
                        ret[n] = self.model.qresult()[0]
                    # if field is TEXT we have to use quotes to
                    # assemble SQL query row in _request_subvalues:
                    # WHERE field = "value"
                    if self.model.columns[n].dt_type == 'TEXT':
                        ret[n] = '"' + ret[n] + '"'
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
                f = self.model.qresults()
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
