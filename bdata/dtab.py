import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, unescape
from bdata import bcol
from prog import filt


class DataTable(object):
    """ this class contains
        modification options of a given table
        with the results of these modification (self.tab)
    """
    def __init__(self, name, proj,
                 init_columns, fill_ttab, need_rewrite):
        """
        init_columns:def(DataTable) - delegate for self.columns initialization
        fill_ttab:def(DataTable) - delegate that fills temporary table
                                   self.ttab_name
        """
        self.id = -1
        self.proj = proj
        self.comment = ''
        # =========== data declaration
        # sql data
        self.name = name
        # sql data table name: containes tabname data and
        # additional rows representing status of each entry
        self.ttab_name = '_tmp ' + name

        # columns information
        # self columns in order they should be viewed
        self.all_columns = []
        # columns which are visible for user
        self.visible_columns = []

        # query options
        # group column ids list
        self.group_by = []
        # (column id, "ASC"/"DESC")
        self.ordering = None

        # filters: anon filters belong to current tables,
        #          named filters are taked from self.proj.
        #          used_filters contain ids of both anon and named filters
        self.all_anon_filters = []
        self.used_filters = []

        # table data on python side: fetched data which should be shown.
        self.tab = ViewedData(self)

        # data initialization
        init_columns(self)   # fills self.columns, self.visible columns
        self._create_ttab()  # create temporary sql table
        fill_ttab(self)      # ... and fills it

        # reorders columns (categorical->real),
        # fills all columns, visible columns, sets ids
        self._complete_columns_lists()

    # ---------------------- assembling procedures
    def _original_collist(self, with_type=True):
        collist = []
        if with_type:
            tp = "{} {}"
        else:
            tp = "{}"
        for c in filter(lambda x: x.is_original(), self.all_columns):
            if c.name != 'id':
                collist.append(tp.format(c.sql_line(False),
                                         c.sql_data_type()))
            else:
                collist.append(tp.format('"id"', "INTEGER UNIQUE"))
            collist.append(tp.format(
                c.status_column.sql_line(False), "INTEGER DEFAULT 0"))
        return collist

    def _create_ttab(self):
        # [(colname, col sql type)]
        collist = self._original_collist()

        # choose proper name
        self.query("SELECT name FROM sqlite_master WHERE type='table'")
        enames = [x[0] for x in self.qresults()]
        if self.ttab_name in enames:
            for i in range(999999):
                nm = self.ttab_name + str(i)
                if nm not in enames:
                    self.ttab_name = nm
                    break
            else:
                raise Exception("Failed to create temporary table {}".format(
                        self.ttab_name))

        # create table
        qr = """CREATE TABLE "{0}" ({1})
        """.format(self.ttab_name, ', '.join(collist))
        self.query(qr)

    def _complete_columns_lists(self):
        ac, self.all_columns, self.visible_columns = self.all_columns, [], []
        for v in filter(lambda x: x.is_category(), ac):
            self.all_columns.append(v)
            self.visible_columns.append(v)
        for v in filter(lambda x: not x.is_category(), ac):
            self.all_columns.append(v)
            self.visible_columns.append(v)
        for c in self.all_columns:
            c.set_id(self.proj.new_id())

    def set_id(self, iden):
        self.id = iden

    @staticmethod
    def _fix_column_order(lst):
        c1 = list(filter(lambda x: x.is_category(), lst))
        c2 = list(filter(lambda x: not x.is_category(), lst))
        lst.clear()
        lst.extend(c1)
        lst.extend(c2)

    # ================ database manipulations
    def destruct(self):
        """ removes temporary table from :memory: """
        qr = 'DROP TABLE "{}"'.format(self.ttab_name)
        self.query(qr)

    def rename_ttab(self, newname):
        qr = 'ALTER TABLE "{}" RENAME TO "{}"'.format(
                self.ttab_name, newname)
        self.query(qr)
        self.ttab_name = newname

    def write_to_db(self):
        ' flushes current data to A database if needed '
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
        self.proj.sql.commit()

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
                oc = self.get_column(iden=self.ordering[0])
            except KeyError:
                self.ordering = None
        if group:
            gc = [self.get_column(iden=x) for x in group]
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
            # get filters from self.used_filters
            filters = [self.get_filter(iden=x) for x in self.used_filters]
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
    # def merge_categories(self, categories, delim):
    #     """ Creates new column build of merged list of categories,
    #            places it after the last visible category column
    #         categories -- list of ColumnInfo entries
    #         returns newly created column or
    #                 None if this column already exists
    #     """
    #     if len(categories) < 2:
    #         return None
    #     # create column
    #     col = bcol.collapsed_categories(categories, delim)
    #     # check if this merge was already done
    #     if col.name in self.columns.keys():
    #         return None
    #     self.add_column(col)
    #     # place to the visible columns list
    #     for i, c in enumerate(self.visible_columns):
    #         if not c.is_category():
    #             break
    #     else:
    #         i += 1
    #     self.visible_columns.insert(i, col)
    #     return col

    # def remove_column(self, col):
    #     try:
    #         self.columns.pop(col.name)
    #     except:
    #         pass
    #     try:
    #         self.all_columns.remove(col)
    #     except:
    #         pass
    #     try:
    #         self.visible_columns.remove(col)
    #     except:
    #         pass

    # def add_column(self, col, pos=None, is_visible=False):
    #     if col.name not in self.columns:
    #         self.columns[col.name] = col
    #         if not col.is_category():
    #             self.set_data_group_function()
    #         if pos is None:
    #             pos = len(self.columns)
    #     else:
    #         # if column already presents in current data
    #         if pos is None:
    #             pos = self.all_columns.index(col)
    #         # temporary remove column from lists
    #         try:
    #             self.all_columns.remove(col)
    #         except:
    #             pass
    #         try:
    #             self.visible_columns.remove(col)
    #         except:
    #             pass
    #     # maximum position for category column
    #     # or minimum for data column
    #     limpos = 0
    #     while limpos < len(self.all_columns) and\
    #             self.all_columns[limpos].is_category():
    #         limpos += 1
    #     # add to all_columns
    #     if col.is_category():
    #         pos = min(pos, limpos)
    #     else:
    #         pos = max(pos, limpos)
    #     self.all_columns.insert(pos, col)
    #     # visibles
    #     vis_set = set(self.visible_columns)
    #     if is_visible:
    #         vis_set.add(col)
    #     self._assemble_visibles(vis_set)

    #     if col.is_original():
    #         self.set_need_rewrite(True)

    # def _inscribe_column_into_dict(self, cname, dct):
    #     col = self.columns[cname]
    #     # return if column is not original
    #     if not col.is_original():
    #         return
    #     # return if new and old dictionary have same keys
    #     if not col.uses_dict(None):
    #         diff = set(col.repr_delegate.dict.keys()).difference(dct.keys())
    #         if len(diff) == 0:
    #             return
    #     if col.dt_type in ['INT', 'REAL', 'ENUM', 'BOOL']:
    #         # remove all entries outside availible keys
    #         ivals = ', '.join(map(str, dct.keys()))
    #         qr = 'UPDATE "{0}" SET {1} = NULL WHERE {1} NOT IN ({2})'.format(
    #             self.ttab_name, col.sql_line(), ivals)
    #         self.query(qr)
    #     elif col.dt_type in ['TEXT']:
    #         # convert text into int keys
    #         raise NotImplementedError
    #     self.query("SELECT CHANGES()")
    #     # if smth was changed require rewrite
    #     if self.qresult()[0] > 0:
    #         self.set_need_rewrite(True)

    # def convert_column(self, cname, newtype, dct=None):
    #     """ converts given column to a given newtype
    #     """
    #     # TODO use common procedure from bdata/convert.py
    #     col = self.columns[cname]
    #     if col.dt_type in ['BOOL', 'ENUM'] and newtype == 'INT':
    #         col.set_repr_delegate(bcol.IntRepr())
    #     elif col.dt_type in ['INT', 'BOOL', 'ENUM']\
    #             and newtype == 'BOOL':
    #         self._inscribe_column_into_dict(cname, dct)
    #         col.set_repr_delegate(bcol.BoolRepr(dct))
    #     elif col.dt_type in ['INT', 'BOOL', 'ENUM']\
    #             and newtype == 'ENUM':
    #         self._inscribe_column_into_dict(cname, dct)
    #         col.set_repr_delegate(bcol.EnumRepr(dct))
    #     else:
    #         raise NotImplementedError

    # def remove_entries(self, flt):
    #     """ Removes entries according to a given filter,
    #         returns number of removed lines.
    #     """
    #     qr = 'DELETE FROM "{}" WHERE ({})'.format(
    #         self.ttab_name, flt.to_sqlline(self))
    #     self.query(qr)
    #     self.query("SELECT CHANGES()")
    #     ret = self.qresult()[0]
    #     if ret > 0:
    #         self.reset_id()
    #     return ret

    def reset_id(self):
        """ Fills id column with 1, 2, 3, ... values.
            Does not check if id values are already in correct order.
            Set need_rewrite to true.
        """
        self.query('SELECT COUNT(*) from "{}"'.format(self.ttab_name))
        nums = range(1, self.qresult()[0] + 1)
        # update filters that use id
        idfilters = list(filter(lambda x: isinstance(x, filt.IdFilter),
                                self.all_anon_filters))
        if len(idfilters) > 0:
            self.query('SELECT id FROM "{}" ORDER BY id'.format(
                self.ttab_name))
            old_id = [x[0] for x in self.qresults() if x[0] is not None]
            for f in idfilters:
                if not f.reset_id(old_id):
                    self.all_anon_filters.remove(f)
        # update id column
        self.query('SELECT rowid FROM "{}" ORDER BY rowid'.format(
            self.ttab_name))
        newold = zip(nums, (x[0] for x in self.qresults()))
        self.query("""
            UPDATE "{}" SET id = ? WHERE rowid = ?
        """.format(self.ttab_name), newold)

    def add_anon_filter(self, f):
        assert f.name is None and f.is_applicable(self)
        if f.id == -1:
            f.set_id(self.proj.new_id())
        self.all_anon_filters.append(f)

    # def set_visibility(self, col, do_show):
    #     is_visible = col in self.visible_columns
    #     if is_visible == do_show:
    #         return
    #     if not do_show:
    #         self.visible_columns.remove(col)
    #     else:
    #         assert col in self.all_columns
    #         vis_set = set(self.visible_columns + [col])
    #         self._assemble_visibles(vis_set)

    # def _assemble_visibles(self, vis_set):
    #     self.visible_columns.clear()
    #     for c in self.all_columns:
    #         if c in vis_set:
    #             self.visible_columns.append(c)

    # def add_filter(self, f, use=True):
    #     if not f.is_applicable(self):
    #         raise Exception('filter "{}" can not be used with "{}"'.format(
    #             f.name, self.name))
    #     f.proj = self.proj
    #     if f.name is None:
    #         if f not in self.all_anon_filters:
    #             self.all_anon_filters.append(f)
    #     else:
    #         if f not in self.proj.named_filters:
    #             self.proj.named_filters.append(f)
    #     if use and f not in self.used_filters:
    #         self.used_filters.append(f)

    # def set_filter_usage(self, f, use):
    #     if not use:
    #         if f in self.used_filters:
    #             self.used_filters.remove(f)
    #     elif use and f not in self.used_filters:
    #         if f.name and f in self.proj.named_filters:
    #             self.used_filters.append(f)
    #         if not f.name and f in self.all_anon_filters:
    #             self.used_filters.append(f)

    # def set_named_filters(self, filtlist):
    #     self.proj.set_named_filters(filtlist)

    # def set_anon_filters(self, filtlist):
    #     self.all_anon_filters.clear()
    #     for f in filtlist:
    #         if f.is_applicable(self):
    #             self.all_anon_filters.append(f)

    # def set_active_filters(self, filtlist):
    #     self.used_filters.clear()
    #     for f in filtlist:
    #         self.set_filter_usage(f, True)

    # --------------------- xml
    def to_xml(self, root):
        ET.SubElement(root, "ID").text = str(self.id)
        ET.SubElement(root, "NAME").text = escape(self.name)
        ET.SubElement(root, "COMMENT").text = escape(self.comment)
        # ---- columns
        cur = ET.SubElement(root, "COLUMNS")
        for c in self.all_columns:
            nd = ET.SubElement(cur, "E")
            c.to_xml(nd)
            redstatus = self.redstatus_bytearray(c)
            if redstatus is not None:
                ET.SubElement(nd, 'REDSTATUS').text = redstatus
        # visible columns
        ET.SubElement(cur, "VIS").text =\
            ' '.join([str(x.id) for x in self.visible_columns])
        # ----- filters
        cur = ET.SubElement(root, "FILTERS")
        # anonymous filters
        for f in self.all_anon_filters:
            n = ET.SubElement(cur, "ANON")
            f.to_xml(n)
        # used filter
        ET.SubElement(cur, "USED").text =\
            ' '.join([str(x) for x in self.used_filters])

        # ----- ordering
        if self.ordering is not None:
            ET.SubElement(root, "ORDER_BY").text =\
                "{} {}".format(self.ordering[0], self.ordering[1])

        # ----- grouping
        if self.group_by:
            ET.SubElement(root, "GROUP_BY").text =\
                ' '.join([str(i) for i in self.group_by])

    @classmethod
    def from_xml(cls, root, proj):
        def init_columns(self):
            self.all_columns = []
            for nd in root.findall('COLUMNS/E'):
                self.all_columns.append(bcol.ColumnInfo.from_xml(nd, proj))
            if not self.all_columns or self.all_columns[0].name != 'id':
                raise Exception("unique id column was not found")

        def fill_ttab(self):
            ls = [x.sql_line() for x in self.all_columns if x.is_original()]
            qr = 'INSERT INTO "{0}" ({1}) SELECT {1} from "{2}"'.format(
                self.ttab_name, ", ".join(ls), self.name)
            self.query(qr)

        # create table
        name = unescape(root.find('NAME').text)
        ret = cls(name, proj, init_columns, fill_ttab, False)

        # id
        ret.set_id(int(root.find('ID').text))
        # comment
        fnd = root.find('COMMENT')
        if fnd and fnd.text:
            ret.comment = unescape(fnd.text)
        # visible columns
        visc = map(int, root.find('COLUMNS/VIS').text.split())
        ret.visible_columns = [ret.get_column(iden=i) for i in visc]
        # red status
        if root.findall('COLUMNS/E/REDSTATUS'):
            raise NotImplementedError
        # filters
        for flt in root.findall('FILTERS/ANON'):
            f = filt.Filter.from_xml(flt)
            ret.all_anon_filters.append(f)
        fnd = root.find('FILTERS/USED')
        if fnd and fnd.text:
            uf = map(int, fnd.text.split())
            ret.used_filters = list(uf)
        # order
        fnd = root.find('ORDER_BY')
        if fnd and fnd.text:
            a = fnd.text.split()
            ret.ordering = (int(a[0]), a[1])
        # group
        fnd = root.find('GROUP_BY')
        if fnd and fnd.text:
            ret.group_by = map(int, fnd.text.split())
        return ret

    # ------------------------ info and checks
    def get_column(self, name=None, ivis=None, iden=None):
        if name is not None:
            return next(filter(lambda x: x.name == name, self.all_columns),
                        None)
        if ivis is not None:
            try:
                return self.visible_columns[ivis]
            except IndexError:
                return None
        if iden is not None:
            return next(filter(lambda x: x.id == iden, self.all_columns),
                        None)

    def get_filter(self, name=None, iden=None):
        if name is not None:
            return self.proj.get_filter(name=None)
        if iden is not None:
            for f in self.all_anon_filters:
                if f.id == iden:
                    return f
            return self.proj.get_filter(iden=iden)

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

    def column_visindex(self, col=None, iden=None, name=None):
        if col is not None:
            return self.visible_columns.index(col)
        else:
            col = self.get_column(name=name, iden=iden)
            return self.column_visindex(col)

    def get_categories(self):
        """ -> [ColumnInfo] (excluding id)"""
        return list(filter(lambda x: x.is_category(),
                           self.all_columns))[1:]

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

    # def is_valid_column_name(self, nm, shortnm=None):
    #     """ checks if nm could be used as a new column name for this tab
    #         raises Exception if negative
    #     """
    #     # name
    #     self.proj.is_possible_column_name(nm)
    #     cnames = list(map(lambda x: x.upper(), self.columns.keys()))
    #     if nm.upper() in cnames:
    #         raise Exception(
    #             'Column name "{}" already exists in the table'.format(nm))
    #     # short name
    #     if shortnm is not None:
    #         self.proj.is_possible_column_name(shortnm)
    #     return True

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

    # def row_definition(self, r):
    #     """ dictionary which uniquely defines the row (including grouping)
    #     """
    #     return self.tab.rows[r].definition

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
        col = self.get_column(cname)
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
            qr = self._compile_query([self.get_column(cname)], False)
            self.query(qr)
            return [x[0] for x in self.qresults()]

    def get_distinct_column_raw_vals(self, cname, is_global=True, sort=False):
        """ -> distinct vals in global scope (ignores filters, groups etc)
               or local scope (including all settings)
        """
        col = self.get_column(cname)
        if is_global:
            s = "ORDER BY {}".format(col.sql_line()) if sort else ''
            qr = 'SELECT DISTINCT({0}) FROM "{1}" {2}'.format(
                    col.sql_line(), self.ttab_name, s)
        else:
            if sort:
                bu = self.ordering
                self.ordering = (col.name, 'ASC')
            qr = self._compile_query([col], status_adds=False,
                                     group_adds=False)
            if sort:
                self.ordering = bu
            qr = qr.replace("SELECT", "SELECT DISTINCT", 1)
        self.query(qr)
        return [x[0] for x in self.qresults()]

    def get_distinct_column_vals(self, cname, is_global=True):
        """ -> distinct vals in global scope (ignores filters, groups etc)
               or local scope (including all settings)
        """
        col = self.get_column(cname)
        rv = self.get_distinct_column_raw_vals(cname, is_global)
        return [col.repr(x) for x in rv]

    def redstatus_bytearray(self, col):
        """ returns bytearray of column redstatuses if there are
            any positive values, else returns None
        """
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
                for i in self.model.group_by:
                    n = self.model.get_column(iden=i).name
                    try:
                        ret[n] = self.value_by_name(n)
                    except KeyError:
                        # grouped value does not present in the data
                        # hence we make a query through the id
                        qr = 'SELECT {} from "{}" WHERE id={}'.format(
                            self.model.get_column(n).sql_line(),
                            self.model.ttab_name,
                            self.id)
                        self.model.query(qr)
                        ret[n] = self.model.qresult()[0]
                    # if field is TEXT we have to use quotes to
                    # assemble SQL query row in _request_subvalues:
                    # WHERE field = 'value'
                    if self.model.get_column(n).dt_type == 'TEXT':
                        ret[n] = "'" + ret[n] + "'"
                return ret

        def _request_subvalues(self):
            if self.n_sub_values == 1:
                self.sub_values = [self.values]
                self.sub_status = [self.status]
            else:
                vc = len(self.model.visible_columns)
                # add additional filters defining this group
                flt = [self.get_filter(iden=x)
                       for x in self.model.used_filters]
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
