import sqlite3
from prog import basic


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


def max_per_list(*args):
    try:
        return max(args)
    except Exception as e:
        basic.ignore_exception(e, 'error: max_per_list')


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
]
registered_sql_functions = [
        ("max_per_list", -1, max_per_list),
        ("cast_txt_to_int", 1, cast_txt_to_int),
        ("cast_txt_to_real", 1, cast_txt_to_real),
        ("cast_real_to_int", 1, cast_real_to_int),
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


connection = SqlConnection()
