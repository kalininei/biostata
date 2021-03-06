import os
import os.path
import xml.etree.ElementTree as ET
import base64
from prog import basic

# directory where configuration information (like .biostatarc, .biostata-log)
# will be stored
_progoutpath = '.'
if not __debug__:
    if os.name == 'nt':
        try:
            # on windows try to read config.txt file which should be located
            # in main executable directory
            cfgpath = os.path.join(os.path.dirname(__file__),
                                   '..', 'config.txt')
            if os.path.exists(cfgpath):
                out = None
                with open(cfgpath, 'r') as fid:
                    lines = fid.readlines()
                    for ln in lines:
                        if ln.strip().startswith('datadir:'):
                            out = ln[8:].strip()
                            break
                if out is not None and os.path.exists(out):
                    _progoutpath = os.path.abspath(out)
        except Exception as e:
            basic.ignore_exception(e)
            _progoutpath = '.'
    if _progoutpath == '.':
        # otherwise get user local folder
        _progoutpath = os.path.expanduser('~')


class BiostataOptions:
    def __init__(self):
        # representation
        self.basic_font_size = 10
        self.show_bool_as = 'icons'   # [icons, codes, 0/1, Yes/No]
        self.real_numbers_prec = 6

        # external programs
        self.external_xlsx_editor = ''
        self.external_txt_editor = ''

        # start behaviour
        self.open_recent_db_on_start = 0

        # additional data
        # list of recently opened databases
        self.recent_db = []
        # main window state and geometry encoded in b64
        self.mw_state = ''
        self.mw_geom = ''

    @staticmethod
    def rcfile():
        return os.path.join(_progoutpath, '.biostatarc')

    @staticmethod
    def logfile():
        return os.path.join(_progoutpath, '.biostata-log')

    def set_mainwindow_state(self, state, geom):
        'state, geom -- bytearray data'
        self.mw_geom = base64.b64encode(geom).decode('utf-8')
        self.mw_state = base64.b64encode(state).decode('utf-8')

    def mainwindow_state(self):
        '->state, geom in bytearray'
        return base64.b64decode(self.mw_state), base64.b64decode(self.mw_geom)

    def save(self):
        from bgui import qtcommon
        from prog import basic
        import prog
        try:
            root = ET.Element('BiostataOptions')
            root.attrib['version'] = prog.version

            # representation
            orepr = ET.SubElement(root, "TABLE")
            ET.SubElement(ET.SubElement(orepr, 'FONT'), 'SIZE').text = str(
                    self.basic_font_size)
            ET.SubElement(orepr, 'BOOL_AS').text = self.show_bool_as
            ET.SubElement(orepr, 'REAL_PREC').text = str(
                    self.real_numbers_prec)

            # external programs
            exrepr = ET.SubElement(root, "EXTERNAL")
            ET.SubElement(exrepr, "XLSX").text = self.external_xlsx_editor
            ET.SubElement(exrepr, "TXT").text = self.external_txt_editor

            # behaviour
            brepr = ET.SubElement(root, "BEHAVIOUR")
            ET.SubElement(brepr, "OPEN_RECENT").text = str(
                    self.open_recent_db_on_start)

            # recent databases
            rdb = ET.SubElement(root, "RECENT_DB")
            for r in self.recent_db:
                ET.SubElement(rdb, "PATH_DB").text = r

            # forms positions
            wnd = ET.SubElement(root, "WINDOWS")
            qtcommon.save_window_positions(wnd)
            # mainwindow state
            mainstate = ET.SubElement(wnd, "MAIN")
            ET.SubElement(mainstate, "GEOMETRY").text = self.mw_geom
            ET.SubElement(mainstate, "STATE").text = self.mw_state

            # save to file
            basic.xmlindent(root)
            tree = ET.ElementTree(root)
            tree.write(self.rcfile(), xml_declaration=True, encoding='utf-8')
        except Exception as e:
            basic.ignore_exception(e)

    def load(self):
        from bgui import qtcommon

        def _read_field(path, frmt, attr, islist=False):
            ndval = lambda x: (frmt(x) if x is not None
                               else '' if frmt == str else None)
            try:
                if not islist:
                    self.__dict__[attr] = ndval(root.find(path).text)
                else:
                    self.__dict__[attr].clear()
                    for nd in root.findall(path):
                        self.__dict__[attr].append(ndval(nd.text))
            except Exception as e:
                basic.ignore_exception(e, "xmlnode {} failed".format(path))

        try:
            root = ET.parse(self.rcfile())
        except Exception as e:
            basic.ignore_exception(e, "Loading options file failed")
            return

        _read_field('TABLE/FONT/SIZE', int, 'basic_font_size')
        _read_field('TABLE/BOOL_AS', str, 'show_bool_as')
        _read_field('TABLE/REAL_PREC', int, 'real_numbers_prec')
        _read_field('EXTERNAL/XLSX', str, 'external_xlsx_editor')
        _read_field('EXTERNAL/TXT', str, 'external_txt_editor')
        _read_field('BEHAVIOUR/OPEN_RECENT', int, 'open_recent_db_on_start')
        _read_field('RECENT_DB/PATH_DB', str, 'recent_db', True)

        # set window sizes
        posnode = root.find('WINDOWS')
        if posnode is not None:
            qtcommon.set_window_positions(posnode)

        _read_field('WINDOWS/MAIN/GEOMETRY', str, 'mw_geom')
        _read_field('WINDOWS/MAIN/STATE', str, 'mw_state')

    def add_db_path(self, dbpath):
        if dbpath in self.recent_db:
            self.recent_db.remove(dbpath)
        self.recent_db.insert(0, dbpath)
        self.recent_db = self.recent_db[:10]

    def default_project_filename(self):
        if self.open_recent_db_on_start and len(self.recent_db) > 0:
            return self.recent_db[0]
