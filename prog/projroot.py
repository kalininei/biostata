import copy
import pathlib
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import prog
from prog import bsqlproc
from prog import basic
from prog import valuedict


class ProjectDB:
    def __init__(self):
        self.idc = basic.IdCounter()

        # connection to a database with main = :memory:
        self.sql = bsqlproc.connection
        self._curname = "New database"
        self._curdir = pathlib.Path.cwd()
        # project data
        self.dictionaries = []
        self.named_filters = []
        self.data_tables = []

        self.initialize()

    def initialize(self):
        self.idc.reset()
        self._curname = "New database"
        self.named_filters.clear()
        self.data_tables.clear()
        self.dictionaries.clear()
        # add default dictionaries
        self.add_dictionary(copy.deepcopy(valuedict.dict_az))
        self.add_dictionary(copy.deepcopy(valuedict.dict_09))
        self.add_dictionary(copy.deepcopy(valuedict.dict_01))
        self.add_dictionary(copy.deepcopy(valuedict.dict_truefalse))
        self.add_dictionary(copy.deepcopy(valuedict.dict_yesno))

    def new_id(self):
        return self.idc.new()

    def to_xml(self, nd, wtabs=True):
        # current proj and cwd
        ET.SubElement(nd, "PROJ").text = escape(str(self._curname))
        ET.SubElement(nd, "CWD").text = escape(str(self._curdir.resolve()))
        # dictionaries
        cur = ET.SubElement(nd, "DICTIONARIES")
        for d in self.dictionaries:
            dc = ET.SubElement(cur, "E")
            d.to_xml(dc)
        # filters
        cur = ET.SubElement(nd, "FILTERS")
        for d in self.named_filters:
            dc = ET.SubElement(cur, "E")
            d.to_xml(dc)
        # table states
        if wtabs:
            cur = ET.SubElement(nd, "TABLES")
            for d in self.data_tables:
                dc = ET.SubElement(cur, "E")
                d.to_xml(dc)

    # ================= Database procedures
    def set_current_filename(self, filedb):
        # change current directory
        self._curname = filedb
        if filedb != 'New database':
            self._curdir = pathlib.Path(filedb).parent

    def close_main_database(self):
        for t in self.data_tables:
            t.destruct()
        self.sql.detach_database('A')
        self.initialize()

    def commit_all_changes(self):
        basic.log_message("Commit into {}".format(self._curname))
        if not self.sql.has_A:
            raise Exception("No file based database found")

        # state information
        root = ET.Element('BiostataData')
        root.set('version', prog.version)
        self.to_xml(root)
        root = ET.tostring(root, encoding='utf-8', method='xml').decode()
        self.sql.query('UPDATE A._INFO_ SET "status" = ?', [(root,)])

        # remove tables which are not present in data_tables
        self.sql.query("SELECT name FROM A.sqlite_master WHERE type='table'")
        tabs = [x[0] for x in self.sql.qresults()]
        tabs.remove('_INFO_')
        extabs = [x.name for x in self.data_tables]
        for t in filter(lambda x: x not in extabs, tabs):
            self.sql.query('DROP TABLE A."{}"'.format(t))

        # write tables information
        for table in self.data_tables:
            table.write_to_db()

    def finish(self):
        basic.log_message("Close connection")
        self.close_main_database()
        self.sql.close_connection()

    # ================= Modificators
    def add_filter(self, filt):
        self.valid_tech_string("Filter name", filt.name)
        if filt.name in [x.name for x in self.named_filters]:
            raise Exception("Filter {} already "
                            "presents in the project".format(filt.name))
        if filt.id == -1:
            filt.set_id(self.new_id())
        else:
            self.idc.include(filt.id)
        self.named_filters.append(filt)

    def add_dictionary(self, dct):
        self.valid_tech_string("Dict name", dct.name)
        if dct.name in [x.name for x in self.dictionaries]:
            raise Exception("Dictionary {} already "
                            "presents in the project".format(dct.name))
        if dct.id == -1:
            dct.set_id(self.new_id())
        else:
            self.idc.include(dct.id)
        self.dictionaries.append(dct)

    def add_table(self, tab):
        self.is_valid_table_name(tab.name)

        maxid = max([tab.id] + [c.id for c in tab.all_columns])
        self.idc.include(maxid)
        for c in [tab] + tab.all_columns:
            if c.id == -1:
                c.set_id(self.new_id())

        tab.proj = self
        self.data_tables.append(tab)

    # #######################################################################
    # def set_named_filters(self, filtlist, useall=False):
    #     # remove all existing filters
    #     for dt in self.data_tables:
    #         for f in self.named_filters:
    #             dt.set_filter_usage(f, False)
    #     self.named_filters.clear()
    #     # add new
    #     self.named_filters.extend([f for f in filtlist if f.name])
    #     if useall:
    #         for dt in self.data_tables:
    #             for f in self.named_filters:
    #                 dt.set_filter_usage(f, True)

    # def remove_dictionary(self, k, lastcheck=True):
    #     try:
    #         d = self.dictionaries[k]
    #     except KeyError:
    #         return
    #     # forbid removing of last type dictionary.
    #     if lastcheck:
    #         if d.dt_type == 'ENUM' and len(self.enum_dictionaries()) == 1:
    #             raise Exception(
    #                 "Can not remove last enum dictionary {}".format(k))
    #         if d.dt_type == 'BOOL' and len(self.bool_dictionaries()) == 1:
    #             raise Exception(
    #                 "Can not remove last bool dictionary {}".format(k))
    #     # search for columns containing this dict and convert them to int.
    #     for t in self.data_tables:
    #         for column in t.columns.values():
    #             if column.uses_dict(d):
    #                 t.convert_column(column.name, 'INT')
    #     # search for filters containing this dict and remove them
    #     for f in self.all_filters():
    #         if f.uses_dict(d):
    #             self.remove_filter_anywhere(f)
    #     # remove from project
    #     self.dictionaries.pop(k)

    # def change_dictionaries(self, oldnew):
    #     """ odlnew - {'olddict name': newdict}
    #     """
    #     try:
    #         newd = oldnew['__new__']
    #         oldnew.pop('__new__')
    #     except KeyError:
    #         newd = []
    #     # 1) remove dictionaries
    #     for k in [k1 for k1, v1 in oldnew.items() if v1 is None]:
    #         self.remove_dictionary(k, False)

    #     # 2) change dictionaries
    #     for k, v in [(k1, v1) for k1, v1 in oldnew.items()
    #                  if v1 is not None]:
    #         d = self.dictionaries[k]
    #         what_changed = valuedict.Dictionary.compare(d, v)
    #         if 'keys added' in what_changed or\
    #               'keys removed' in what_changed:
    #             # remove filters
    #             for f in self.all_filters():
    #                 if f.uses_dict(d):
    #                     self.remove_filter_anywhere(f)
    #         elif 'name' in what_changed:
    #             # changed name in filters
    #             for f in filter(lambda x: x.uses_dict(d),
    #                             self.all_filters()):
    #                 f.change_dict_name(d.name, v.name)
    #         # convert columns
    #         for t in self.data_tables:
    #             for c in filter(lambda x: x.uses_dict(d),
    #                             t.columns.values()):
    #                 t.convert_column(c.name, v.dt_type, v)
    #         # update dictionaries
    #         d.copy_from(v)

    #     # 3) remove changed dicts
    #     for nm in filter(lambda x: x in self.dictionaries, oldnew.keys()):
    #         self.dictionaries.pop(nm)

    #     # 4) add new dicts
    #     for d in filter(lambda x: x is not None, oldnew.values()):
    #         self.dictionaries[d.name] = d
    #     for d in newd:
    #         self.dictionaries[d.name] = d

    # def remove_filter_anywhere(self, f):
    #     for t in self.data_tables:
    #         if f in t.used_filters:
    #             t.used_filters.remove(f)
    #         if f.name is None and f in t.all_anon_filters:
    #             t.all_anon_filters.remove(f)
    #             return
    #     if f.name is not None and f in self.named_filters:
    #         self.named_filters.remove(f)

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

    def is_possible_table_name(self, nm):
        m = 'Table name "{}"'.format(nm)
        self.valid_tech_string(m, nm)

    def is_valid_table_name(self, nm):
        """ checks if nm could be used as a new table name
            raises Exception if negative
        """
        m = 'Table name "{}"'.format(nm)
        self.valid_tech_string(m, nm)
        cnames = list(map(lambda x: x.name.upper(), self.data_tables))
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

    # def all_filters(self):
    #     ret = self.named_filters[:]
    #     for t in self.data_tables:
    #         ret.extend(t.all_anon_filters)
    #     return ret

    # def get_table_names(self):
    #     return [x.table_name() for x in self.data_tables]

    # def get_named_filter(self, name):
    #     try:
    #         return next(x for x in self.named_filters if x.name == name)
    #     except StopIteration:
    #         raise KeyError

    def get_table(self, name=None, iden=None):
        if name is not None:
            return next(filter(lambda x: x.table_name() == name,
                               self.data_tables))
        if iden is not None:
            return next(filter(lambda x: x.id == iden, self.data_tables))

    def get_dictionary(self, name=None, iden=None):
        if name is not None:
            return next(filter(lambda x: x.name == name,
                               self.dictionaries))
        if iden is not None:
            return next(filter(lambda x: x.id == iden, self.dictionaries))

    def get_filter(self, name=None, iden=None):
        if name is not None:
            return next(filter(lambda x: x.name == name,
                               self.named_filters), None)
        if iden is not None:
            return next(filter(lambda x: x.id == iden, self.named_filters),
                        None)

    def enum_dictionaries(self):
        return list(filter(lambda x: x.dt_type == "ENUM",
                           self.dictionaries))

    def bool_dictionaries(self):
        return list(filter(lambda x: x.dt_type == "BOOL",
                           self.dictionaries))

    # def need_save(self):
    #     return self._curname != 'New database'

    # def close_connection(self):
    #     self.connection.close()

    # def curdir(self):
    #     return str(self._curdir)
