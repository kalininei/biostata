import copy
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, unescape
from ast import literal_eval
from prog import basic, bsqlproc


class ColumnInfo:
    def __init__(self, name):
        self.name = name
        self.shortname = name
        self.dim = ''
        self.comment = ''
        self.dt_type = None
        self.real_data_groupfun = 'AVG'
        # delegates
        self.repr_delegate = None
        self.sql_delegate = None

    # ----------- basic functional
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
        ET.SubElement(root, 'SQL_REAL_GROUP').text =\
            escape(self.real_data_groupfun)
        self.repr_delegate.state_xml(root)
        self.sql_delegate.state_xml(root)
        return ET.tostring(root, encoding='utf-8', method='xml').decode()

    def is_category(self):
        return self.dt_type != "REAL"

    def sql_group_fun(self):
        if self.is_category():
            return 'category_group'
        else:
            return self.real_data_groupfun

    def set_sql_delegate(self, d):
        self.sql_delegate = d
        d.column = self

    def set_repr_delegate(self, d):
        self.repr_delegate = d
        self.dt_type = d.dt_type()

    def rename(self, newname):
        self.name = newname
        if hasattr(self, 'status_column'):
            self.status_column.rename('_status ' + newname)

    # ------------ delegated to repr_delegate
    def repr(self, x):
        try:
            return self.repr_delegate.repr(x)
        except:
            return None

    def from_repr(self, x):
        try:
            return self.repr_delegate.from_repr(x)
        except:
            return None

    def col_type(self):
        '-> INT, TEXT, ENUM (dict), ... '
        return self.repr_delegate.col_type()

    def uses_dict(self, dct):
        """ whether this column uses Dictionary dct.
            If dct=None -> checks if there are no dicts at all.
            if dct is string -> checks dictionary name
        """
        return self.repr_delegate.uses_dict(dct)

    def same_representation(self, a):
        return self.repr_delegate.same_representation(a.repr_delegate)

    # ------------- delegated to sql_delegate
    def sql_line(self, grouping=False):
        return self.sql_delegate.sql_line(grouping)

    def is_original(self):
        return self.sql_delegate.is_original()

    # ------------- static and class methods
    @staticmethod
    def are_same(collist):
        if len(collist) < 2:
            return True

        for i in range(len(collist)-1):
            if not collist[i].same_representation(collist[i+1]):
                return False
        return True


# ================== Repr delegates
class _BasicRepr:
    def repr(self, x):
        raise NotImplementedError

    def from_repr(self, x):
        raise NotImplementedError

    def col_type(self):
        raise NotImplementedError

    def dt_type(self):
        return self.col_type().split(maxsplit=1)[0]

    def same_representation(self, rep):
        return isinstance(rep, self.__class__)

    def uses_dict(self, dct):
        return dct is None

    def state_xml(self, root):
        pass

    def copy(self):
        return copy.deepcopy(self)

    @staticmethod
    def default(tp, dct=None):
        if tp == 'INT':
            return IntRepr()
        elif tp == 'TEXT':
            return TextRepr()
        elif tp == 'REAL':
            return RealRepr()
        elif tp == 'BOOL':
            return BoolRepr(dct)
        elif tp == 'ENUM':
            return EnumRepr(dct)


class IntRepr(_BasicRepr):
    def repr(self, x):
        return int(x)

    def from_repr(self, x):
        if isinstance(x, str):
            return round(float(x)) if x is not None else None
        else:
            return int(x) if x is not None else None

    def col_type(self):
        return "INT"


class TextRepr(_BasicRepr):
    def repr(self, x):
        return str(x)

    def from_repr(self, x):
        return x

    def col_type(self):
        return "TEXT"


class RealRepr(_BasicRepr):
    def repr(self, x):
        return float(x)

    def from_repr(self, x):
        return float(x)

    def col_type(self):
        return "REAL"


class EnumRepr(_BasicRepr):
    def __init__(self, d):
        self.dict = d

    def repr(self, x):
        return self.dict.key_to_value(x)

    def from_repr(self, x):
        return self.dict.value_to_key(x)

    def col_type(self):
        return "ENUM ({})".format(self.dict.name)

    def uses_dict(self, dct):
        return self.dict is dct or (isinstance(dct, str) and
                                    dct == self.dict.name)

    def same_representation(self, rep):
        return super().same_representation(rep) and self.dict is rep.dict

    def copy(self):
        return self.__class__(self.dict)


class BoolRepr(EnumRepr):
    def col_type(self):
        return "BOOL ({})".format(self.dict.name)


# ======================= Sql delegates
class _BasicSqlDelegate:
    def __init__(self):
        # this is assigned when delegate connects to column
        self.column = None

    def copy(self):
        bu, self.column = self.column, None
        ret = copy.deepcopy(self)
        self.column = bu
        return ret

    def state_xml(self, root):
        pass


class OriginalSqlDelegate(_BasicSqlDelegate):
    def sql_line(self, grouping=False):
        if not grouping:
            return '"{}"'.format(self.column.name)
        else:
            return '{}("{}")'.format(
                self.column.sql_group_fun(), self.column.name)

    def is_original(self):
        return True


class FuncSqlDelegate(_BasicSqlDelegate):
    def __init__(self, deps):
        super().__init__()
        # list of ColumnInfo from which this function gets its arguments
        self.deps = deps
        self._sql_fun = None
        self.use_before_grouping = None
        # string representation of function which was used to build self.
        self.function_type = None
        # serializable arguments for calling function_type
        self.kwargs = {}

    def is_original(self):
        return False

    def sql_line(self, grouping=False):
        if grouping and self.use_before_grouping:
            return "{}({}({}))".format(
                self.column.sql_group_fun(), self._sql_fun,
                ", ".join([x.sql_line(False) for x in self.deps]))
        elif grouping and not self.use_before_grouping:
            return "{}({})".format(self._sql_fun, ", ".join(
                [x.sql_line(True) for x in self.deps]))
        else:
            return "{}({})".format(self._sql_fun, ", ".join(
                [x.sql_line(False) for x in self.deps]))

    def state_xml(self, root):
        super().state_xml(root)

        ET.SubElement(root, 'BEFORE_GROUPING').text =\
            str(int(self.use_before_grouping))
        ET.SubElement(root, 'FUNCTION').text =\
            escape(self.function_type)
        ET.SubElement(root, "ARGUMENTS").text =\
            escape(str([x.name for x in self.deps]))
        ET.SubElement(root, "DESCRIPTION").text = escape(str(self.kwargs))


class OrigStatusColumn(ColumnInfo):
    def __init__(self, parent):
        nm = '_status ' + parent.name
        super().__init__(nm)
        self.dt_type = 'BOOL'
        self.set_sql_delegate(OriginalSqlDelegate())

    def sql_group_fun(self):
        return 'MAX'


class FuncStatusColumn(ColumnInfo):
    def __init__(self, parent):
        nm = "_status " + parent.name
        super().__init__(nm)
        self.dt_type = "BOOL"

        deps = [p.status_column for p in parent.sql_delegate.deps]
        sql = FuncSqlDelegate(deps)
        sql._sql_fun = 'max_per_list'
        sql.use_before_gouping = True
        self.set_sql_delegate(sql)

    def sql_group_fun(self):
        return 'MAX'


# ========================= Constructors
def build_original_column(name, tp, dct=None, state_xml=None):
    ret = ColumnInfo(name)
    ret.set_repr_delegate(_BasicRepr.default(tp, dct))
    ret.set_sql_delegate(OriginalSqlDelegate())

    if state_xml is not None:
        ret.real_data_groupfun = unescape(
            state_xml.find('SQL_REAL_GROUP').text)

    # status column
    ret.status_column = OrigStatusColumn(ret)
    return ret


def explicit_build(proj, name, tp_name, dict_name=None):
    dct = proj.get_dictionary(dict_name) if dict_name else None
    return build_original_column(name, tp_name, dct)


def build_id():
    return build_original_column('id', "INT")


def build_deep_copy(orig, newname=None):
    """ copies, breaks all dependencies. Resulting column is original. """
    bu1, bu2 = orig.repr_delegate, orig.sql_delegate
    orig.repr_delegate, orig.sql_delegate = None, None
    if hasattr(orig, 'status_column'):
        bu3 = orig.status_column
        orig.status_column = None
    ret = copy.deepcopy(orig)
    if newname:
        ret.name = newname
        ret.shortname = ret.name
    orig.repr_delegate, orig.sql_delegate = bu1, bu2
    ret.set_repr_delegate(bu1.copy())
    ret.set_sql_delegate(OriginalSqlDelegate())
    if hasattr(orig, 'status_column'):
        orig.status_column = bu3
        ret.status_column = OrigStatusColumn(ret)
    return ret


def build_deep_copy_wo_sql(orig, newname=None):
    ''' copies all, keeps old repr and status, sql_delegate = None'''
    bu = orig.repr_delegate, orig.sql_delegate, orig.status_column
    orig.repr_delegate, orig.sql_delegate, orig.status_column = (None,)*3
    ret = copy.deepcopy(orig)
    if newname:
        ret.name = newname
        ret.shortname = ret.name
    orig.repr_delegate, orig.sql_delegate, orig.status_column = bu
    ret.set_repr_delegate(orig.repr_delegate)
    ret.status_column = orig.status_column
    return ret


def restore_function_column(name, func_name, columns, **kwargs):
    if func_name == "collapsed_categories":
        return collapsed_categories(columns, kwargs['delimiter'])
    else:
        raise Exception("unknown function name {}".format(kwargs['func_name']))


def build_from_db(proj, table, name):
    """ builds a column and places it into table.columns[name].

        In order to keep dependencies recursive procedure is used.
        Hence single run of this procedure in case of functional columns
        may result in reading and placing all parent columns.
    """
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
    state = ET.fromstring(f[5]) if f[5] else None
    if f[6]:
        # ------ original column
        ret = build_original_column(name, f[0], state, dct)
    else:
        # ------ functional column
        colnames = literal_eval(unescape(state.find("ARGUMENTS").text))
        # create all arguments recursively
        colargs = [build_from_db(proj, table, x) for x in colnames]
        kwargs = literal_eval(unescape(
            state.find("DESCRIPTION").text))
        func_name = unescape(state.find("FUNCTION"))
        ret = restore_function_column(name, func_name, colargs, **kwargs)
        ret.set_repr_delegate(_BasicRepr.default(f[0], dct))

    # ----------- fill basic data
    ret.shortname = f[3] if f[3] is not None else name
    ret.dim = f[2] if f[2] else ''
    ret.comment = f[4] if f[4] else ''
    table.columns[name] = ret
    return ret


def build_function_sql_delegate(deps, before_grouping, func, func_type, kw):
    ret = FuncSqlDelegate(deps)
    ret._sql_fun = bsqlproc.connection.build_lambda_func(func)
    ret.function_type = func_type
    ret.use_before_grouping = before_grouping
    ret.kwargs = kw

    return ret


# ======================= functional columns list
def collapsed_categories(columns, delimiter='-'):
    def func(*args):
        try:
            ret = []
            for c, x in zip(columns, args):
                if x is not None:
                    ret.append(str(c.repr(x)))
                else:
                    ret.append('##')
            return delimiter.join(ret)
        except Exception as e:
            basic.ignore_exception(e, "collapse error. " + str(args))

    name = delimiter.join([x.shortname for x in columns])
    kwargs = {'delimiter': delimiter}
    rep = _BasicRepr.default("TEXT")
    sql = build_function_sql_delegate(columns, True, func,
                                      "collapsed_categories", kwargs)
    ret = ColumnInfo(name)
    ret.set_repr_delegate(rep)
    ret.set_sql_delegate(sql)

    ret.status_column = FuncStatusColumn(ret)
    return ret
