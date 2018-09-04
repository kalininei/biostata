import collections
import sqlite3
from bdata import dtab
from bdata import bsqlproc


class Dictionary:
    def __init__(self, name, dt_type, keys, values, comments=None):
        if dt_type not in ["BOOL", "ENUM"]:
            raise Exception("Invalid dictionary data type")

        if None in keys:
            raise Exception("Some keys are not set")

        if len(set(keys)) != len(keys):
            raise Exception("Dictionary keys are not unique")

        if len(set(values)) != len(values):
            raise Exception("Dictionary values are not unique")

        if len(values) != len(keys):
            raise Exception("Dictionary values and keys have different size")

        if len(values) < 2:
            raise Exception("Dictionary set needs at least 2 values")

        if dt_type == "BOOL":
            if len(keys) != 2 or keys[0] != 0 or keys[1] != 1:
                raise Exception("Bool dictionary keys should contain "
                                "0 and 1 only")
        self.dt_type = dt_type
        self.name = name
        self.kvalues = collections.OrderedDict()
        self.vkeys = collections.OrderedDict()
        self.kcomments = collections.OrderedDict()
        for k, v in zip(keys, values):
            self.kvalues[k] = v
            self.vkeys[v] = k
            self.kcomments[k] = ''

        if comments is not None:
            for k, coms in zip(self.kvalues.keys(), comments):
                self.kcomments[k] = coms

    def key_to_value(self, key):
        return self.kvalues[key]

    def value_to_key(self, value):
        return self.vkeys[value]

    def comment_from_key(self, key):
        return self.kcomments[key]

    def values(self):
        return list(self.vkeys.keys())

    def keys(self):
        return list(self.kvalues.keys())

    @staticmethod
    def from_db(name, proj):
        qr = """
            SELECT type, comment FROM _DICTIONARIES_ WHERE name="{}"
        """.format(name)
        proj.cursor.execute(qr)
        f = proj.cursor.fetchone()
        dt_type = f[0]

        tnm = '"_DICTIONARY {}"'.format(name)
        qr = "SELECT key, value, comment FROM {}".format(tnm)
        proj.cursor.execute(qr)
        f = proj.cursor.fetchall()
        keys = [x[0] for x in f]
        values = [x[1] for x in f]
        comments = [x[2] for x in f]

        return Dictionary(name, dt_type, keys, values, comments)


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
            self.dictionaries[a[0]] = Dictionary.from_db(a[0], self)

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
            raise Exception(
                "{} already exists in the present project.".format(m))

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

    def add_dictionary(self, dct):
        if dct.name not in self.dictionaries.keys():
            self.dictionaries[dct.name] = dct
        else:
            raise Exception("Dictionary already presents in the project")

    def enum_dictionaries(self):
        return list(filter(lambda x: x.dt_type == "ENUM",
                           self.dictionaries.values()))

    def bool_dictionaries(self):
        return list(filter(lambda x: x.dt_type == "BOOL",
                           self.dictionaries.values()))

    def close_connection(self):
        self.connection.close()
