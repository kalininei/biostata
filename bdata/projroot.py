import collections
import sqlite3
from bdata import dtab
from bdata import bsqlproc


class Category:
    def __init__(self, name, proj):
        self.proj = proj
        self.name = name
        qr = """
            SELECT shortname, iscategory, type, dim
                FROM _DATA_TYPES_ WHERE name="{}"
        """.format(self.name)
        proj.cursor.execute(qr)
        f = proj.cursor.fetchone()
        self.shortname = f[0] if f[0] else self.name
        self.is_category = f[1]
        self.dt_type = f[2]
        self.dim = f[3]

        # possible values for enum and boolean data
        # integers to strings converter
        self.possible_values_short = collections.OrderedDict()
        self.possible_values = collections.OrderedDict()
        if self.dt_type in ["ENUM", "BOOLEAN"]:
            tnm = '"_DATA_TYPE {}"'.format(self.name)
            qr = """
                SELECT value, shortname, name FROM {}
            """.format(tnm)
            proj.cursor.execute(qr)
            f = proj.cursor.fetchall()
            vls = [x[0] for x in f]
            snm = [x[1] for x in f]
            nm = [x[2] for x in f]
            for i, s, n in zip(vls, snm, nm):
                if s is None:
                    s = n
                self.possible_values_short[i] = s
                self.possible_values[i] = n


class ProjectDB:
    def __init__(self, filedb):
        # connection
        self.connection = sqlite3.connect(filedb)
        bsqlproc.init_connection(self.connection)
        self.cursor = self.connection.cursor()

        # data types
        self.data_types = []
        self.cursor.execute("SELECT name FROM _DATA_TYPES_")
        for a in self.cursor.fetchall():
            self.data_types.append(Category(a[0], self))

        # named filters
        self.named_filters = []

        # data tables
        # (after data_types cause the latter is used in table constructors)
        self.data_tables = []
        self.cursor.execute("SELECT name FROM _DATA_TABLES_")
        for a in self.cursor.fetchall():
            self.data_tables.append(dtab.DataTable(a[0], self))

    def set_named_filters(self, filtlist, useall=False):
        # remove all existing filters
        for dt in self.data_tables:
            for f in self.named_filters:
                dt.set_filter_usage(f, False)
        self.named_filters.clear()
        # add new
        self.named_filters.extend([f for f in filtlist if f.name])
        if useall:
            for dt in self.data_tables:
                for f in self.named_filters:
                    dt.set_filter_usage(f, True)

    def get_category(self, name):
        for c in self.data_types:
            if c.name == name:
                return c
        raise KeyError(name)

    def close_connection(self):
        self.connection.close()
