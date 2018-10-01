import sqlite3
import numpy as np
import numbers
from prog import basic
from bmat import stats


def group_repr(c):
    """ c -> ...[c] """
    return '...[' + str(c) + ']'


class _Grouping1:
    def __init__(self):
        self.vals = []

    def step(self, v):
        self.vals.append(v)


class _GroupingA:
    def __init__(self):
        self.vals = []

    def step(self, *args):
        self.vals.append([v for v in args if v is not None])


class CategoryGrouping(_Grouping1):
    """ If all processed values are equal returns it,
        Otherwise returns None
    """
    def __init__(self):
        super().__init__()

    def finalize(self):
        s = set(self.vals)
        if len(s) == 1:
            return self.vals[0]
        else:
            return None


class MedianDataGrouping(_Grouping1):
    def __init__(self):
        super().__init__()

    def finalize(self):
        if not self.vals:
            return None
        indp = int(len(self.vals)/2)
        s = sorted(self.vals)
        if len(self.vals) % 2 == 0:
            return (s[indp] + s[indp-1])/2
        else:
            return s[indp]


class MedianPDataGrouping(_Grouping1):
    def __init__(self):
        super().__init__()

    def finalize(self):
        if not self.vals:
            return None
        indp = int(len(self.vals)/2)
        s = sorted(self.vals)
        return s[indp]


class MedianMDataGrouping(_Grouping1):
    def __init__(self):
        super().__init__()

    def finalize(self):
        if not self.vals:
            return None
        indp = int(len(self.vals)/2)
        s = sorted(self.vals)
        return s[indp-1]


class _XYFunGrouping:
    _pool_size = 10

    def __init__(self):
        self.sz = 0
        self.csz = self._pool_size
        self.x = np.zeros(self._pool_size)
        self.y = np.zeros(self._pool_size)

    def step(self, x, y):
        # pass non number values
        if not (isinstance(x, numbers.Number) and
                isinstance(y, numbers.Number)):
            return
        # adjust size if needed
        if self.sz == self.csz:
            self.csz += self._pool_size
            self.x = np.resize(self.x, self.csz)
            self.y = np.resize(self.y, self.csz)
        # add values
        self.x[self.sz] = x
        self.y[self.sz] = y
        self.sz += 1

    def finalize(self):
        if self.sz == 0:
            return None
        sv = np.argsort(self.x[:self.sz])
        a = self.x[sv]
        b = self.y[sv]
        au, cnt = np.unique(a, return_counts=True)
        if np.size(au) == np.size(a):
            return self.worker(a, b)
        # treat repeated x-axis values
        bu = np.copy(b)
        ibcur = 0
        icur = 0
        for x in np.nditer(cnt):
            bu[ibcur] = np.mean(b[icur:icur+x])
            ibcur += 1
            icur += x
        return self.worker(au, bu[:ibcur])

    def worker(self, a, b):
        raise NotImplementedError


class IntegralDataGrouping(_XYFunGrouping):
    def __init__(self):
        super().__init__()

    def worker(self, a, b):
        return np.trapz(b, a)


_build_regression_grouping_ret = {}


def build_regression_grouping(tp, ngroup):
    'tp = linear, log, power'
    global _build_regression_grouping_ret

    if ngroup in _build_regression_grouping_ret:
        return _build_regression_grouping_ret[ngroup]

    if tp == 'linear':
        rfunc = stats.linear_regression
    elif tp == 'log':
        rfunc = stats.log_regression
    elif tp == 'power':
        rfunc = stats.power_regression
    else:
        assert False

    class _Runner(_XYFunGrouping):
        def __init__(self):
            super().__init__()
            self.wrk = None

        def start(self, obj):
            if self.wrk is None:
                self.sz = 0
                self.wrk = obj
                self.ret = [None] * 5

        def end(self, obj):
            self.wrk = None

        def finalize(self):
            r = super().finalize()
            self.wrk = None
            return r

        def worker(self, a, b):
            self.ret = rfunc(a, b)

    r = _Runner()

    class _Basic:
        runner = r

        def __init__(self):
            self.runner.start(self)

        def step(self, x, y):
            if self.runner.wrk == self:
                self.runner.step(x, y)

        def finalize(self):
            if self.runner.wrk is not None:
                self.runner.finalize()

    class Slope(_Basic):
        def __init__(self):
            super().__init__()

        def finalize(self):
            super().finalize()
            return self.runner.ret[0]

    class Intercept(_Basic):
        def __init__(self):
            super().__init__()

        def finalize(self):
            super().finalize()
            return self.runner.ret[1]

    class StdErr(_Basic):
        def __init__(self):
            super().__init__()

        def finalize(self):
            super().finalize()
            return self.runner.ret[2]

    class SlopeErr(_Basic):
        def __init__(self):
            super().__init__()

        def finalize(self):
            super().finalize()
            return self.runner.ret[3]

    class CorrCoef(_Basic):
        def __init__(self):
            super().__init__()

        def finalize(self):
            super().finalize()
            return self.runner.ret[4]

    ret = {'a': Slope, 'b': Intercept, 'stderr': StdErr,
           'slopeerr': SlopeErr, 'corrcoef': CorrCoef}
    _build_regression_grouping_ret[ngroup] = ret
    return ret


def max_per_list(*args):
    return max(args)


def row_max(*args):
    try:
        return max(filter(lambda x: x is not None, args))
    except ValueError:
        return None


def row_min(*args):
    try:
        return min(filter(lambda x: x is not None, args))
    except ValueError:
        return None


def row_sum(*args):
    try:
        return sum(filter(lambda x: x is not None, args))
    except ValueError:
        return None


def row_average(*args):
    a = list(filter(lambda x: x is not None, args))
    if len(a) == 0:
        return None
    else:
        return sum(a)/len(a)


def row_median(*args):
    a = list(sorted(filter(lambda x: x is not None, args)))
    if len(a) == 0:
        return None
    else:
        indp = int(len(a)/2)
        if len(a) % 2 == 0:
            return (a[indp] + a[indp-1])/2
        else:
            return a[indp]


def row_product(*args):
    a = list(filter(lambda x: x is not None, args))
    if len(a) == 0:
        return None
    else:
        ret = 1
        for x in a:
            ret *= x
        return ret


def cast_txt_to_real(a):
    try:
        return float(a)
    except (ValueError, TypeError):
        return None


def cast_txt_to_int(a):
    try:
        return round(float(a))
    except (ValueError, TypeError):
        return None


def cast_real_to_int(a):
    if a is None or a >= 9223372036854775807 or a <= -9223372036854775808:
        return None
    else:
        return round(a)

# those functions will be added to each connection passed to TabModel
registered_aggregate_functions = [
        ("category_group", 1, CategoryGrouping),
        ("median", 1, MedianDataGrouping),
        ("medianp", 1, MedianPDataGrouping),
        ("medianm", 1, MedianMDataGrouping),
        ("xy_integral", 2, IntegralDataGrouping),
]
registered_sql_functions = [
        ("max_per_list", -1, max_per_list),
        ("cast_txt_to_int", 1, cast_txt_to_int),
        ("cast_txt_to_real", 1, cast_txt_to_real),
        ("cast_real_to_int", 1, cast_real_to_int),
        ("row_min", -1, row_min),
        ("row_max", -1, row_max),
        ("row_sum", -1, row_sum),
        ("row_average", -1, row_average),
        ("row_product", -1, row_product),
        ("row_median", -1, row_median),
]


class SqlConnection:
    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.init_connection()
        self.cursor = self.connection.cursor()
        self._i_sql_functions = 1
        self.has_A = False

    def close_connection(self):
        self.connection.close()

    def query(self, qr, dt=None):
        basic.log_message(" ".join(qr.split()))
        if dt is None:
            self.cursor.execute(qr)
        else:
            self.cursor.executemany(qr, dt)

    def qresult(self):
        return self.cursor.fetchone()

    def qresults(self):
        return self.cursor.fetchall()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def attach_database(self, alias, fn):
        self.detach_database(alias)
        self.query('ATTACH DATABASE "{}" AS "{}"'.format(fn, alias))
        if alias == 'A':
            self.has_A = True

    def detach_database(self, alias):
        try:
            # Fails to detach with 'locked' error without this commit
            self.connection.commit()
            self.query('DETACH DATABASE "{}"'.format(alias))
        except:
            pass
        if alias == 'A':
            self.has_A = False

    def init_connection(self):
        for r in registered_aggregate_functions:
            self.connection.create_aggregate(*r)
        for r in registered_sql_functions:
            self.connection.create_function(*r)

    def build_lambda_func(self, lambda_func):
        def sql_func(*args):
            return lambda_func(*args)

        nm = "sql_custom_func_{}".format(self._i_sql_functions)
        self.connection.create_function(nm, -1, sql_func)
        self._i_sql_functions += 1
        return nm

    def build_aggr_func(self, aggr_class):
        nm = "sql_custom_aggr_func_{}".format(self._i_sql_functions)
        self.connection.create_aggregate(nm, -1, aggr_class)
        self._i_sql_functions += 1
        return nm

    def swap_tables(self, tab1, tab2):
        tmpname = '_alter{} {}'.format(basic.uniint(), tab1)
        qr = 'ALTER TABLE "{}" RENAME TO "{}"'.format(tab1, tmpname)
        self.query(qr)
        qr = 'ALTER TABLE "{}" RENAME TO "{}"'.format(tab2, tab1)
        self.query(qr)
        qr = 'ALTER TABLE "{}" RENAME TO "{}"'.format(tmpname, tab2)
        self.query(qr)


connection = SqlConnection()
