import sys
import copy
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, unescape
from ast import literal_eval
from prog import basic, bsqlproc


class ColumnInfo:
    def __init__(self, name):
        self.id = -1
        self.name = name
        self.shortname = name
        self.dim = ''
        self.comment = ''
        self.dt_type = None
        self.real_data_groupfun = 'AVG'
        # delegates
        self.repr_delegate = None
        self.sql_delegate = None

    def set_id(self, iden):
        self.id = iden

    # ----------- basic functional
    def sql_data_type(self):
        if self.dt_type in ["ENUM", "BOOL", "INT"]:
            return "INTEGER"
        elif self.dt_type == "REAL":
            return "REAL"
        elif self.dt_type == "TEXT":
            return "TEXT"

    def to_xml(self, root):
        ET.SubElement(root, "ID").text = str(self.id)
        ET.SubElement(root, "NAME").text = escape(self.name)
        ET.SubElement(root, "SHORTNAME").text = escape(self.shortname)
        ET.SubElement(root, "DIM").text = escape(self.dim)
        ET.SubElement(root, "COMMENT").text = escape(self.comment)
        ET.SubElement(root, "GROUPFUN").text = escape(self.real_data_groupfun)
        self.repr_delegate.to_xml(root)
        self.sql_delegate.to_xml(root)

    @classmethod
    def from_xml(cls, root, proj):
        name = unescape(root.find('NAME').text)
        ret = cls(name)
        ret.set_id(int(root.find('ID').text))
        ret.shortname = unescape(root.find('SHORTNAME').text)
        fnd = root.find('DIM')
        if fnd and fnd.text:
            ret.dim = unescape(fnd.text)
        fnd = root.find('COMMENT')
        if fnd and fnd.text:
            ret.comment = unescape(fnd.text)
        ret.real_data_groupfun = unescape(root.find('GROUPFUN').text)
        ret.set_repr_delegate(_BasicRepr.from_xml(root, proj))
        ret.set_sql_delegate(_BasicSqlDelegate.from_xml(root))
        if ret.is_original():
            ret.status_column = OrigStatusColumn(ret)
        else:
            ret.status_column = None  # FuncStatusColumn(ret)
        return ret

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

    def description(self):
        ret = []
        ret.append(self.sql_delegate.description())
        ret.append('')
        if self.comment:
            ret.append(self.comment)
        return '\n'.join(ret)

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

    def to_xml(self, root):
        ET.SubElement(root, "REPR").text = self.__class__.__name__

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

    @staticmethod
    def from_xml(root, proj):
        cls = getattr(sys.modules[__name__], root.find('REPR').text)
        if cls in [IntRepr, TextRepr, RealRepr]:
            return cls()
        if cls in [EnumRepr, BoolRepr]:
            idct = int(root.find('DICT').text)
            dct = proj.get_dictionary(iden=idct)
            return cls(dct)
        assert False, str(cls)


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

    def to_xml(self, root):
        super().to_xml(root)
        ET.SubElement(root, "DICT").text = str(self.dict.id)

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

    @staticmethod
    def from_xml(root):
        if root.find('SQL_ORIG') is not None:
            return OriginalSqlDelegate()
        elif root.find('SQL_AGGR_FUNC') is not None:
            return AggrFuncSqlDelegate.from_xml(root)
        elif root.find('SQL_FUNC') is not None:
            return FuncSqlDelegate.from_xml(root)
        assert False


class OriginalSqlDelegate(_BasicSqlDelegate):
    def sql_line(self, grouping=False):
        if not grouping:
            return '"{}"'.format(self.column.name)
        else:
            return '{}("{}")'.format(
                self.column.sql_group_fun(), self.column.name)

    def is_original(self):
        return True

    def to_xml(self, root):
        ET.SubElement(root, "SQL_ORIG")

    def description(self):
        return "Original data\nGroup with {}".format(
                self.column.real_data_groupfun)


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

    def to_xml(self, root):
        cur = ET.SubElement(root, "SQL_FUNC")
        ET.SubElement(cur, 'BEFORE_GROUPING').text =\
            str(int(self.use_before_grouping))
        ET.SubElement(cur, 'FUNCTION').text =\
            escape(self.function_type)
        ET.SubElement(cur, "ARGUMENTS").text =\
            ' '.join([str(x.id) for x in self.deps])
        ET.SubElement(cur, "DESCRIPTION").text = escape(str(self.kwargs))

    @staticmethod
    def from_xml(root):
        # temporary fill deps with id.
        # fill_deps procedure should be called after all columns are built
        # to fill deps and build self.sql_fun
        nd = root.find('SQL_FUNC')
        ret = FuncSqlDelegate([])
        ret.use_before_grouping = bool(int(
            nd.find('BEFORE_GROUPING').text))
        ret.function_type = unescape(nd.find('FUNCTION').text)
        ret.deps = list(map(int, nd.find('ARGUMENTS').text.split()))
        ret.kwargs = literal_eval(unescape(nd.find('DESCRIPTION').text))
        return ret

    def fill_deps(self, tab):
        deps = []
        for i in self.deps:
            deps.append(tab.get_column(iden=i))
        sql = build_function_sql_delegate(
                deps, self.use_before_grouping, None,
                self.function_type, self.kwargs)
        self.deps = sql.deps
        self._sql_fun = sql._sql_fun

    def description(self):
        ret = ['Row function: {}'.format(self.function_type)]
        ret.append('args: {}'.format(', '.join([x.name for x in self.deps])))
        if self.use_before_grouping:
            ret.append('used before grouping')
        else:
            ret.append('used after grouping')
        ret.append('params: {}'.format(str(self.kwargs)))
        ret.append("Group with {}".format(self.column.real_data_groupfun))
        return '\n'.join(ret)


class AggrFuncSqlDelegate(_BasicSqlDelegate):
    def __init__(self, deps):
        super().__init__()
        # list of ColumnInfo from which this function gets its arguments
        self.deps = deps
        self._sql_fun = None
        # string representation of function which was used to build self.
        self.function_type = None
        # serializable arguments for calling function_type
        self.kwargs = {}

    def is_original(self):
        return False

    def sql_line(self, grouping=False):
        if not grouping:
            return 'NULL'
        else:
            return "{}({})".format(self._sql_fun, ", ".join(
                [x.sql_line(False) for x in self.deps]))

    def to_xml(self, root):
        cur = ET.SubElement(root, "SQL_AGGR_FUNC")
        ET.SubElement(cur, 'FUNCTION').text =\
            escape(self.function_type)
        ET.SubElement(cur, "ARGUMENTS").text =\
            ' '.join([str(x.id) for x in self.deps])
        ET.SubElement(cur, "DESCRIPTION").text = escape(str(self.kwargs))

    @staticmethod
    def from_xml(root):
        # temporary fill deps with id.
        # fill_deps procedure should be called after all columns are built
        # to fill deps and build self.sql_fun
        nd = root.find('SQL_AGGR_FUNC')
        ret = AggrFuncSqlDelegate([])
        ret.function_type = unescape(nd.find('FUNCTION').text)
        ret.deps = list(map(int, nd.find('ARGUMENTS').text.split()))
        ret.kwargs = literal_eval(unescape(nd.find('DESCRIPTION').text))
        return ret

    def fill_deps(self, tab):
        deps = []
        for i in self.deps:
            deps.append(tab.get_column(iden=i))
        sql = build_aggr_function_sql_delegate(
                deps, None, self.function_type, self.kwargs)
        self.deps = sql.deps
        self._sql_fun = sql._sql_fun

    def description(self):
        ret = ['Aggregate function: {}'.format(self.function_type)]
        ret.append('args: {}'.format(', '.join([x.name for x in self.deps])))
        ret.append('params: {}'.format(str(self.kwargs)))
        return '\n'.join(ret)


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
    dct = proj.get_dictionary(name=dict_name) if dict_name else None
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


def get_sql_func(name, columns, **kwargs):
    if name == 'collapsed_categories':
        delimiter = kwargs['delimiter']

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
        return func
    elif name.startswith('regression'):
        tp = kwargs['tp']
        ngroup = kwargs['group']
        if name == 'regression a':
            return bsqlproc.build_regression_grouping(tp, ngroup)['a']
        if name == 'regression b':
            return bsqlproc.build_regression_grouping(tp, ngroup)['b']
        if name == 'regression stderr':
            return bsqlproc.build_regression_grouping(tp, ngroup)['stderr']
        if name == 'regression slopeerr':
            return bsqlproc.build_regression_grouping(tp, ngroup)['slopeerr']
        if name == 'regression corrcoef':
            return bsqlproc.build_regression_grouping(tp, ngroup)['corrcoef']
    elif name == 'average':
        return 'row_average'
    elif name == 'min':
        return 'row_min'
    elif name == 'max':
        return 'row_max'
    elif name == 'sum':
        return 'row_sum'
    elif name == 'median':
        return 'row_median'
    elif name == 'product':
        return 'row_product'
    elif name == 'xy_integral':
        return 'xy_integral'
    assert False, "unknown function {}".format(name)


def build_function_sql_delegate(deps, before_grouping, func, func_type, kw):
    ret = FuncSqlDelegate(deps)
    if func is None:
        func = get_sql_func(func_type, deps, **kw)
    if isinstance(func, str):
        ret._sql_fun = func
    else:
        ret._sql_fun = bsqlproc.connection.build_lambda_func(func)
    ret.function_type = func_type
    ret.use_before_grouping = before_grouping
    ret.kwargs = kw

    return ret


def build_aggr_function_sql_delegate(deps, func, func_type, kw):
    ret = AggrFuncSqlDelegate(deps)
    if func is None:
        func = get_sql_func(func_type, deps, **kw)
    if isinstance(func, str):
        ret._sql_fun = func
    else:
        ret._sql_fun = bsqlproc.connection.build_aggr_func(func)
    ret.function_type = func_type
    ret.use_before_grouping = False
    ret.kwargs = kw
    return ret


# ======================= functional columns list
def collapsed_categories(columns, delimiter='-'):
    """ collapse categories function
    """
    name = delimiter.join([x.shortname for x in columns])
    rep = _BasicRepr.default("TEXT")
    kwargs = {'delimiter': delimiter}
    sql = build_function_sql_delegate(columns, True, None,
                                      "collapsed_categories", kwargs)
    ret = ColumnInfo(name)
    ret.set_repr_delegate(rep)
    ret.set_sql_delegate(sql)

    ret.status_column = FuncStatusColumn(ret)
    return ret


def custom_tmp_function(name, func, deplist, before_grouping, rettype):
    """ This function type is for temporary usage only.
        It can not be saved and restored
    """
    rep = _BasicRepr.default(rettype)
    sql = build_function_sql_delegate(deplist, before_grouping, func,
                                      "custom_tmp_function", {})
    ret = ColumnInfo(name)
    ret.set_repr_delegate(rep)
    ret.set_sql_delegate(sql)
    ret.status_column = FuncStatusColumn(ret)
    return ret


def simple_row_function(name, args, func, before_group):
    rep = _BasicRepr.default("REAL")
    sql = build_function_sql_delegate(args, before_group, None, func, {})
    ret = ColumnInfo(name)
    ret.set_repr_delegate(rep)
    ret.set_sql_delegate(sql)
    ret.status_column = FuncStatusColumn(ret)
    return ret


def aggregate_integral_function(name, argx, argy):
    rep = _BasicRepr.default("REAL")
    sql = build_aggr_function_sql_delegate(
            [argx, argy], 'xy_integral', 'xy_integral', {})
    ret = ColumnInfo(name)
    ret.set_repr_delegate(rep)
    ret.set_sql_delegate(sql)
    ret.status_column = FuncStatusColumn(ret)
    return ret


def aggregate_regression(argx, argy, tp, out, out_names):
    kwargs = {'group': "{}_{}_{}".format(argx.id, argy.id, tp), 'tp': tp}
    ret = []
    for ct, cn in zip(out, out_names):
        rep = _BasicRepr.default("REAL")
        sql = build_aggr_function_sql_delegate(
            [argx, argy], None, "regression " + ct, kwargs)
        r = ColumnInfo(cn)
        r.set_repr_delegate(rep)
        r.set_sql_delegate(sql)
        r.status_column = FuncStatusColumn(r)
        ret.append(r)
    return ret
