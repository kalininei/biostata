import collections
import sqlite3
from bdata import dtab
from bdata import bsqlproc


class Dictionary:
    def __init__(self, name, proj):
        self.proj = proj
        self.name = name
        qr = """
            SELECT type, comment FROM _DICTIONARIES_ WHERE name="{}"
        """.format(self.name)
        proj.cursor.execute(qr)
        f = proj.cursor.fetchone()
        self.dt_type = f[0]
        self.comment = f[1]

        # possible values for enum and boolean data
        # integers to strings converter
        self.possible_values = collections.OrderedDict()
        self.values_comments = collections.OrderedDict()
        if self.dt_type in ["ENUM", "BOOL"]:
            tnm = '"_DICTIONARY {}"'.format(self.name)
            qr = "SELECT key, value, comment FROM {}".format(tnm)
            proj.cursor.execute(qr)
            f = proj.cursor.fetchall()
            k = [x[0] for x in f]
            v = [x[1] for x in f]
            com = [x[2] for x in f]
            if self.dt_type == "BOOL":
                if len(k) != 2 or 0 not in k or 1 not in k:
                    raise Exception("BOOL dictionary keys should equal"
                                    " 0 and 1")
            for i, s, c in zip(k, v, com):
                self.possible_values[i] = s
                self.values_comments[i] = c


class ProjectDB:
    def __init__(self, filedb):
        # connection
        self.connection = sqlite3.connect(filedb)
        bsqlproc.init_connection(self.connection)
        self.cursor = self.connection.cursor()

        # data types
        self.dictionaries = collections.OrderedDict()
        self.cursor.execute("SELECT name FROM _DICTIONARIES_")
        for a in self.cursor.fetchall():
            self.dictionaries[a[0]] = Dictionary(a[0], self)

        # named filters
        self.named_filters = []

        # data tables
        # (after data_types because the latter is used in table constructors)
        self.data_tables = []
        self.cursor.execute("SELECT name FROM _DATA_TABLES_")
        for a in self.cursor.fetchall():
            self.data_tables.append(dtab.OriginalTable(a[0], self))

    # ================= Modificators
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

    def add_table(self, newdt):
        self.data_tables.append(newdt)

    def remove_table(self, tablename):
        tab = self.get_table(tablename)
        if tab.is_original():
            raise Exception("Can not remove original table.")
        tab.destruct()
        self.data_tables.remove(tab)
        # remove from dependency list
        for t in self.data_tables:
            if not t.is_original() and tab in t.dependencies:
                t.dependencies.remove(tab)

    # ================= Info and data access
    def valid_tech_string(self, descr, nm):
        if not isinstance(nm, str) or not nm.strip():
            raise Exception("{} should be a valid string.".format(descr))
        if nm[0] == '_':
            raise Exception("{} should not start with '_'.".format(descr))
        for c in ['&', '"', "'"]:
            if nm.find(c) >= 0:
                raise Exception("{} should not contain "
                                "ampersand or quotes signs.".format(descr))

    def is_valid_table_name(self, nm):
        """ checks if nm could be used as a new table name
            raises Exception if negative
        """
        m = 'Table name "{}"'.format(nm)
        self.valid_tech_string(m, nm)
        cnames = list(map(lambda x: x.upper(), self.get_table_names()))
        if nm.upper() in cnames:
            raise Exception("{} already exists in present project.".format(m))

    def is_possible_column_name(self, nm):
        """ checks if nm could be used as a new column name
            raises Exception if negative
        """
        m = 'Column name "{}"'.format(nm)
        self.valid_tech_string(m, nm)
        return True

    def get_table_names(self):
        return [x.table_name() for x in self.data_tables]

    def get_named_filter(self, name):
        try:
            return next(x for x in self.named_filters if x.name == name)
        except StopIteration:
            raise KeyError

    def get_table(self, name):
        try:
            return next(x for x in self.data_tables if x.table_name() == name)
        except StopIteration:
            raise KeyError

    def get_dictionary(self, name):
        return self.dictionaries[name]

    def close_connection(self):
        self.connection.close()
