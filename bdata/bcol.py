import xml.etree.ElementTree as ET
from prog import bsqlproc


# ====================== Basic column info
class ColumnInfo:
    def __init__(self):
        self.name = None
        self.shortname = None
        self.dim = None
        self.comment = None
        self.dt_type = None
        self._sql_group_fun = None

    def col_type(self):
        return self.dt_type

    def is_category(self):
        return self.dt_type != "REAL"

    def is_original(self):
        return isinstance(self, OriginalColumnInfo)

    def sql_line(self, grouping=False):
        raise NotImplementedError

    def sql_data_type(self):
        if self.dt_type in ["ENUM", "BOOL", "INT"]:
            return "INTEGER"
        elif self.dt_type == "REAL":
            return "REAL"
        elif self.dt_type == "TEXT":
            return "TEXT"

    def state_xml(self):
        "returns spec. info as xml string"
        root = ET.Element('ColumnState')
        ET.SubElement(root, 'SQL_GROUP_FUN').text = self._sql_group_fun
        self.imp_state(root)
        return ET.tostring(root, encoding='utf-8', method='xml').decode()

    def imp_state(self, root):
        'used to save stuff from functional columns'
        pass

    @staticmethod
    def are_same(collist):
        if len(collist) < 2:
            return True

        def eq(col1, col2):
            if col1.dt_type != col2.dt_type:
                return False
            if col1.dt_type in ["BOOL", "ENUM"]:
                if col1.dict != col2.dict:
                    return False
            return True

        for i in range(len(collist)-1):
            if not eq(collist[i], collist[i+1]):
                return False
        return True


# ====================== Data representation classes
class DataRepr:
    def __init__(self):
        pass

    def repr(self, x):
        raise NotImplementedError

    def from_repr(self, x):
        raise NotImplementedError


class EnumRepr(DataRepr):
    def __init__(self, dct):
        self.dict = dct

    def repr(self, x):
        try:
            return self.dict.key_to_value(x)
        except KeyError:
            return None

    def from_repr(self, x):
        try:
            return self.dict.value_to_key(x)
        except KeyError:
            return None


class SimpleRepr(DataRepr):
    def __init__(self, ptype):
        super().__init__()
        self._ptype = ptype

    def repr(self, x):
        return x

    def from_repr(self, x):
        return self._ptype(x) if x is not None else None


# ======================= Original Columns (present in sql table)
class OriginalColumnInfo(ColumnInfo):
    def __init__(self):
        super().__init__()

    def sql_line(self, grouping=False):
        if not grouping:
            return '"{}"'.format(self.name)
        else:
            return '{}("{}")'.format(self._sql_group_fun, self.name)

    @staticmethod
    def build(name, dt_type, dct=None):
        if dt_type == "INT":
            ret = IntColumnInfo()
        elif dt_type == "TEXT":
            ret = TextColumnInfo()
        elif dt_type == "REAL":
            ret = RealColumnInfo()
        elif dt_type == "BOOL":
            ret = BoolColumnInfo(dct)
        elif dt_type == "ENUM":
            ret = EnumColumnInfo(dct)
        else:
            raise Exception("Unknown column type: {}".format(dt_type))
        ret.name = name
        ret.status_column = StatusColumnInfo(ret)
        return ret


class StatusColumnInfo(OriginalColumnInfo):
    def __init__(self, parent):
        super().__init__()
        self.name = "_status " + parent.name
        self.shortname = self.name
        self.dt_type = "BOOL"
        self._sql_group_fun = 'MAX'


class EnumColumnInfo(OriginalColumnInfo, EnumRepr):
    def __init__(self, dct):
        OriginalColumnInfo.__init__(self)
        EnumRepr.__init__(self, dct)
        self.dt_type = "ENUM"

    def col_type(self):
        return "{} ({})".format(self.dt_type, self.dict.name)


class BoolColumnInfo(OriginalColumnInfo, EnumRepr):
    def __init__(self, dct):
        OriginalColumnInfo.__init__(self)
        EnumRepr.__init__(self, dct)
        self.dt_type = "BOOL"

    def col_type(self):
        return "{} ({})".format(self.dt_type, self.dict.name)


class IntColumnInfo(OriginalColumnInfo, SimpleRepr):
    def __init__(self):
        OriginalColumnInfo.__init__(self)
        SimpleRepr.__init__(self, int)
        self.dt_type = "INT"


class TextColumnInfo(OriginalColumnInfo, SimpleRepr):
    def __init__(self):
        OriginalColumnInfo.__init__(self)
        SimpleRepr.__init__(self, str)
        self.dt_type = "TEXT"


class RealColumnInfo(OriginalColumnInfo, SimpleRepr):
    def __init__(self):
        OriginalColumnInfo.__init__(self)
        SimpleRepr.__init__(self, float)
        self.dt_type = "REAL"


# ========================== Function column: calculated each query
class FunctionColumn(ColumnInfo):
    def __init__(self):
        super().__init__()
        self._sql_fun = None
        self.use_before_grouping = None
        self.deps = []
        # func_name containts function which was used to build this column,
        # other fields are serializable arguments.
        self.kwargs = {}

    def sql_line(self, grouping=False):
        if grouping and self.use_before_grouping:
            return "{}({}({}))".format(
                self._sql_group_fun, self._sql_fun,
                ", ".join([x.sql_line(False) for x in self.deps]))
        elif grouping and not self.use_before_grouping:
            return "{}({})".format(self._sql_fun, ", ".join(
                [x.sql_line(True) for x in self.deps]))
        else:
            return "{}({})".format(self._sql_fun, ", ".join(
                [x.sql_line(False) for x in self.deps]))

    def function_type(self):
        try:
            return self.kwargs['func_name']
        except KeyError:
            return None

    def imp_state(self, root):
        from xml.sax.saxutils import escape

        func = ET.SubElement(root, "FUNCTION")
        ET.SubElement(func, "ARGUMENTS").text =\
            escape(str([x.name for x in self.deps]))
        ET.SubElement(func, "DESCRIPTION").text = escape(str(self.kwargs))


class FuncStatusColumn(FunctionColumn):
    def __init__(self, parent):
        super().__init__()
        self.name = "_status " + parent.name
        self.shortname = self.name
        self.dt_type = "BOOL"
        self._sql_group_fun = "MAX"
        self._sql_fun = "max_per_list"
        self.before_grouping = True
        self.deps = [p.status_column for p in parent.deps]


# ========================= Constructors
def build_from_db(proj, table, name):
    """ builds a column and places it into table.columns[name].

        In order to keep dependencies recursive procedure is used,
        so single run of this procedure in case of functinal columns
        may result in reading and placing all parent columns.
    """
    from ast import literal_eval
    from xml.sax.saxutils import unescape
    # recursion tail
    if name in table.columns:
        return table.columns[name]

    qr = """
        SELECT type, dict, dim, shortname, comment, state, isorig
        FROM A."_COLINFO {}" WHERE colname="{}"
    """.format(table.table_name(), name)
    proj.sql.query(qr)
    f = proj.sql.qresult()
    dct = proj.get_dictionary(f[1]) if f[1] else None
    state = ET.fromstring(f[5])
    if f[6]:
        ret = OriginalColumnInfo.build(name, f[0], dct)
    else:
        colnames = literal_eval(unescape(
            state.find("FUNCTION/ARGUMENTS").text))
        # create all arguments recursively
        [build_from_db(proj, table, x) for x in colnames]
        kwargs = literal_eval(unescape(
            state.find("FUNCTION/DESCRIPTION").text))
        ret = restore_function_column(table, colnames, **kwargs)
    ret.shortname = f[3] if f[3] is not None else name
    ret.dim = f[2]
    ret.dt_type = f[0]
    ret._sql_group_fun = state.find("SQL_GROUP_FUN").text
    ret.comment = f[4]
    table.columns[name] = ret
    return ret


def explicit_build(proj, name, tp_name, dict_name):
    dct = proj.get_dictionary(dict_name) if dict_name else None
    ret = OriginalColumnInfo.build(name, tp_name, dct)
    ret.shortname = name
    ret.dt_type = tp_name
    if ret.is_category():
        ret._sql_group_fun = "category_group"
    else:
        ret._sql_group_fun = "AVG"
    ret.status_column = StatusColumnInfo(ret)
    return ret


def build_id():
    ret = OriginalColumnInfo.build('id', "INT", None)
    ret.shortname = 'id'
    ret.dt_type = 'INT'
    ret._sql_group_fun = 'category_group'
    ret.status_column = StatusColumnInfo(ret)
    return ret


def build_deep_copy(orig, newname=None):
    """ copies, breaks all dependencies. Resulting column is original. """
    if orig.dt_type in ["BOOL", "ENUM"]:
        dct = orig.dict
    else:
        dct = None
    name = orig.name if newname is None else newname
    ret = OriginalColumnInfo.build(name, orig.dt_type, dct)
    ret.shortname = orig.shortname
    ret.dt_type = orig.dt_type
    ret._sql_fun = '"{}"'.format(ret.name)
    ret._sql_group_fun = orig._sql_group_fun
    ret.status_column = StatusColumnInfo(ret)
    return ret


def build_function_column(name, func, deps, before_grouping,
                          dt_type, kw, dct=None):
    # representation class
    if dt_type in ["BOOL", "ENUM"]:
        RepClass = EnumRepr    # noqa
        repargs = (dct,)
    else:
        RepClass = SimpleRepr  # noqa
        if dt_type == "INT":
            repargs = (int,)
        elif dt_type == "TEXT":
            repargs = (str,)
        elif dt_type == "REAL":
            repargs = (float,)

    class FuncCInfo(FunctionColumn, RepClass):
        def __init__(self):
            FunctionColumn.__init__(self)
            RepClass.__init__(self, *repargs)
            self.name = name
            self.shortname = name
            self.dt_type = dt_type
            self.deps = deps
            self.use_before_grouping = before_grouping
            self._sql_fun = bsqlproc.connection.build_lambda_func(func)
            if self.is_category():
                self._sql_group_fun = "category_group"
            else:
                self._sql_group_fun = "AVG"
            self.status_column = FuncStatusColumn(self)
            self.kwargs = kw

    return FuncCInfo()


def collapsed_categories(columns, delimiter='-'):

    def func(*args):
        try:
            ret = []
            for c, x in zip(columns, args):
                if x is not None:
                    ret.append(str(c.repr(x)))
                else:
                    ret.append('  ')
            return delimiter.join(ret)
        except Exception as e:
            print("Collapse error: ", str(e), [c.name for c in columns], args)

    name = delimiter.join([x.shortname for x in columns])
    kwargs = {'func_name': 'collapsed_categories', 'delimiter': delimiter}
    ret = build_function_column(name, func, columns, True, "TEXT", kwargs)
    return ret


def restore_function_column(table, colargs, **kwargs):
    columns = [table.columns[x] for x in colargs]
    if kwargs['func_name'] == "collapsed_categories":
        return collapsed_categories(columns, kwargs['delimiter'])
    else:
        raise Exception("unknown function name {}".format(kwargs['func_name']))
