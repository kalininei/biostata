import os
import pathlib
import collections
from bdata import derived_tabs
from bdata import filt
from prog import bsqlproc
from prog import bopts
from prog import basic
from prog import valuedict


class ProjectDB:
    def __init__(self):
        # connection to a database with main = :memory:
        self.sql = bsqlproc.connection
        self._curname = "New database"
        self._curdir = pathlib.Path.cwd()
        # program options
        self.opts = bopts.BiostataOptions()
        self.opts.load()
        # project data
        self.dictionaries = collections.OrderedDict()
        self.named_filters = []
        self.data_tables = []
        self._tables_to_remove = []

        self.initialize()

    def initialize(self):
        self._curname = "New database"
        self.named_filters.clear()
        self.data_tables.clear()
        self._tables_to_remove.clear()
        self.dictionaries = collections.OrderedDict([
            ('ABC', valuedict.dict_abc),
            ('0-9', valuedict.dict_09),
            ('0-1', valuedict.dict_01),
            ('True/False', valuedict.dict_truefalse),
            ('Yes/No', valuedict.dict_yesno)])

    # ================= Database procedures
    def set_main_database(self, filedb):
        basic.log_message("Opening {}".format(filedb))
        # A - database is changed only at commit events.
        # Operations take place in main database which
        # is located in :memory:
        self.sql.attach_database('A', filedb)

        # data types
        self.dictionaries = collections.OrderedDict()
        try:
            self.sql.query("SELECT name FROM A._DICTIONARIES_")
        except Exception as e:
            basic.ignore_exception(e)
        else:
            for a in self.sql.qresults():
                self.dictionaries[a[0]] = valuedict.Dictionary.from_db(
                        a[0], self)

        # named filters
        self.named_filters = []
        try:
            self.sql.query("SELECT name, description FROM A._FILTERS_")
        except Exception as e:
            basic.ignore_exception(e)
        else:
            for a in self.sql.qresults():
                self.named_filters.append(filt.Filter.from_xml_string(a[1]))

        # data tables
        # (after data_types because the latter is used in table constructors)
        self.data_tables = []
        try:
            self.sql.query("SELECT name, comment, state FROM A._DATA_TABLES_")
        except Exception as e:
            basic.ignore_exception(e)
        else:
            for a in self.sql.qresults():
                tab = derived_tabs.original_table(a[0], self)
                tab.comment = a[1]
                tab.restore_state_by_xml(a[2])
                self.data_tables.append(tab)

        # additional information
        # names of non-actual tables which will be removed at next commit
        self._tables_to_remove = []

        self.set_current_filename(filedb)

    def set_current_filename(self, filedb):
        # change current directory
        self._curdir = pathlib.Path(filedb).parent
        self._curname = filedb

    def close_main_database(self):
        for t in self.data_tables:
            t.destruct()
        self.sql.detach_database('A')
        self.initialize()

    def finish(self):
        basic.log_message("Close connection")
        self.close_main_database()
        self.sql.close_connection()

    def relocate_and_commit_all_changes(self, newfile):
        basic.log_message("Relocate database into {}".format(newfile))
        # 1) delete newfile if it exists
        if pathlib.Path(newfile).exists():
            os.remove(newfile)
        # 2) detach old A database and open newfile as A database
        self.sql.detach_database('A')
        self.sql.attach_database('A', newfile)
        self.set_current_filename(newfile)
        # 3) mark all tables as 'need for rewrite'
        for t in self.data_tables:
            t.set_need_rewrite(True)
        # 4) write data
        self.commit_all_changes()

    def commit_all_changes(self):
        basic.log_message("Commit all changes")
        # data bases
        # 1) additional information
        self._write_tables_current_info()
        # 2) delete all tables which are not needed
        for rtable in self._tables_to_remove:
            self._remove_table_from_db(rtable)
        self._tables_to_remove = []
        # 3) named filters
        self._write_filters()
        # 4) dictionaries
        self._write_dictionaries()
        # 5) all tables to originals
        for table in self.data_tables:
            table.to_original()
            table.write_to_db()
        # commit changes
        self.sql.commit()
        # no need to write tables again until they will be changed
        for table in self.data_tables:
            table.set_need_rewrite(False)

    def _write_tables_current_info(self):
        # _DATA_TABLES_
        r = []
        for tab in self.data_tables:
            r.append([tab.name, tab.comment, tab.current_state_xml()])
        self._create_table_in_db(
            '_DATA_TABLES_', [("name", "TEXT PRIMARY KEY"),
                              ("comment", "TEXT"),
                              ("state", "TEXT")], r)
        # _COLINFO
        for tab in self.data_tables:
            nm = "_COLINFO {}".format(tab.name)
            dt = []
            for col in tab.columns.values():
                # basic
                a = [col.name, col.dt_type, col.dim,
                     col.shortname, col.comment, int(col.is_original())]
                # dictionary
                if not col.uses_dict(None):
                    a.append(col.repr_delegate.dict.name)
                else:
                    a.append(None)
                # details
                a.append(col.state_xml())
                # redstatus
                a.append(tab.redstatus_bytearray(col.name))
                # add to data
                dt.append(a)
            # create table
            self._create_table_in_db(nm, [("colname", "TEXT PRIMARY KEY"),
                                          ("type", "TEXT"),
                                          ("dim", "TEXT"),
                                          ("shortname", "TEXT"),
                                          ("comment", "TEXT"),
                                          ("isorig", "INTEGER"),
                                          ("dict", "TEXT"),
                                          ("state", "TEXT"),
                                          ("redstatus", "BLOB")], dt)

    def _write_dictionaries(self):
        r = []
        for d in self.dictionaries.values():
            r.append([d.name, d.dt_type, d.keys_to_str(),
                      d.values_to_str(), d.comments_to_str()])
        self._create_table_in_db('_DICTIONARIES_',
                                 [("name", "TEXT PRIMARY KEY"),
                                  ("type", "TEXT"),
                                  ("keys", "TEXT"),
                                  ("values", "TEXT"),
                                  ("comments", "TEXT")], r)

    def _write_filters(self):
        r = []
        for d in self.named_filters:
            r.append([d.name, d.to_xml_string()])
        self._create_table_in_db('_FILTERS_',
                                 [("name", "TEXT PRIMARY KEY"),
                                  ("description", "TEXT")], r)

    def _create_table_in_db(self, tabname, collist, datalist):
        """ creates table in A database """
        self._remove_table_from_db(tabname)
        colstring1 = ', '.join(['"{}"'.format(x[0]) for x in collist])
        colstring2 = ', '.join(['"{}" {}'.format(x[0], x[1]) for x in collist])
        self.sql.query('CREATE TABLE A."{}" ({})'.format(tabname, colstring2))
        self.sql.query('INSERT INTO A."{}" ({}) VALUES ({})'.format(
                       tabname,
                       colstring1,
                       ', '.join(['?']*len(collist))),
                       datalist)

    def _remove_table_from_db(self, tabname):
        """ removes table from A database """
        self.sql.query('DROP TABLE IF EXISTS A."{}"'.format(tabname))

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
            self._tables_to_remove.append(tab.table_name())
        tab.destruct()
        self.data_tables.remove(tab)
        del tab

    def change_dictionaries(self, oldnew, shrink=True):
        """ odlnew - {'olddict name': newdict}
        """
        removed_filters = []
        # 1) remove dictionaries
        for k in [k1 for k1, v1 in oldnew.items() if v1 is None]:
            d = self.dictionaries[k]
            # search for columns containing this dict and convert them to int.
            for t in self.data_tables:
                for column in t.columns.values():
                    if column.uses_dict(d):
                        t.convert_column(column.name, 'INT')
            # search for filters containing this dict and remove them
            for f in self.all_filters():
                if f.uses_dict(d):
                    removed_filters.append(f)
            # remove dictionary
            self.dictionaries.pop(k)

        # 2) change dictionaries
        newnames = False
        for k, v in [(k1, v1) for k1, v1 in oldnew.items() if v1 is not None]:
            d = self.dictionaries[k]
            what_changed = valuedict.Dictionary.compare(d, v)
            if 'name' in what_changed:
                newnames = True
                # changed name in filters
                for f in filter(lambda x: x.uses_dict(d), self.all_filters()):
                    f.change_dict_name(d.name, v.name)
            if shrink and 'keys removed' in what_changed:
                # shrink column data
                for t in self.data_tables:
                    for column in t.columns.values():
                        if column.uses_dict(d):
                            # create fake filter and use it to shrink data
                            t.convert_column(column.name, 'INT')
                            flt = filt.Filter.filter_by_datalist(
                                t, column, v.keys(), True)
                            t.remove_entries(flt)
                            t.convert_column(column.name, d.dt_type, d)
            # update dictionaries
            d.copy_from(v)
        if newnames:
            d2 = collections.OrderedDict()
            for v in self.dictionaries.values():
                d2[v.name] = v
            self.dictionaries = d2

        # 3) remove filters
        for f in removed_filters:
            self.remove_filter_anywhere(f)

    def remove_filter_anywhere(self, f):
        for t in self.data_tables:
            if f in t.used_filters:
                t.used_filters.remove(f)
            if f.name is None and f in t.all_anon_filters:
                t.all_anon_filters.remove(f)
                return
        if f.name is not None and f in self.named_filters:
            self.named_filters.remove(f)

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

    def all_filters(self):
        ret = self.named_filters[:]
        for t in self.data_tables:
            ret.extend(t.all_anon_filters)
        return ret

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

    def need_save(self):
        return self._curname != 'New database'

    def close_connection(self):
        self.connection.close()

    def curdir(self):
        return str(self._curdir)
