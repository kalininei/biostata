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
        self.xml_saved = basic.BSignal()
        self.xml_loaded = basic.BSignal()

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

    def curdir(self):
        return str(self._curdir)

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
        # others
        self.xml_saved.emit(nd)

    def monitor_recent_db(self, opts):
        def fun(nd):
            if self._curname != 'New database':
                opts.add_db_path(self._curname)
        self.xml_loaded.add_subscriber(fun)
        self.xml_saved.add_subscriber(fun)

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
        maxid = max([tab.id] + [c.id for c in tab.all_columns] +
                    [f.id for f in tab.all_anon_filters])
        self.idc.include(maxid)
        for c in [tab] + tab.all_columns:
            if c.id == -1:
                c.set_id(self.new_id())

        tab.proj = self
        self.data_tables.append(tab)

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

    def get_table(self, name=None, iden=None):
        if name is not None:
            return next(filter(lambda x: x.table_name() == name,
                               self.data_tables))
        if iden is not None:
            return next(filter(lambda x: x.id == iden, self.data_tables))

    def get_dictionary(self, name=None, iden=None):
        if name is not None:
            return next(filter(lambda x: x.name == name, self.dictionaries),
                        None)
        if iden is not None:
            return next(filter(lambda x: x.id == iden, self.dictionaries),
                        None)

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
