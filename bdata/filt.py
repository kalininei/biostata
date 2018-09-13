import copy
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, unescape


def possible_values_list(column, operation, datatab):
    ret = []

    def append_col_names(tp):
        for c in datatab.columns.values():
            if c is not column and c.dt_type == tp:
                ret.append('"{}"'.format(c.name))

    if column.dt_type == "INT":
        if operation != "one of":
            append_col_names("INT")
    elif column.dt_type == "REAL":
        append_col_names("REAL")
    elif column.dt_type == "ENUM":
        ret.extend(column.repr_delegate.dict.values())
    elif column.dt_type == "BOOL":
        ret.append(column.repr_delegate.dict.values()[0] + " (False)")
        ret.append(column.repr_delegate.dict.values()[1] + " (True) ")
        append_col_names("BOOL")
    elif column.dt_type == "TEXT":
        append_col_names("TEXT")
    else:
        raise NotImplementedError
    return ret


def factions(dt_type):
    a0 = ["==", "!="]
    ae = ["NULL", "not NULL"]
    a1 = [">", "<", ">=", "<="]
    if dt_type == "INT":
        a = a1 + ["one of"]
    elif dt_type == "REAL":
        a = a1
    elif dt_type == "BOOL":
        a = []
    elif dt_type == "ENUM":
        a = []
    elif dt_type == "TEXT":
        a = []
    else:
        raise NotImplementedError
    return copy.deepcopy(a0 + a + ae)

fconcat = ["AND", "OR"]

fopenparen = ["", "(", "( (", "( ( ("]

fcloseparen = ["", ")", ") )", ") ) )", ")...)"]


class Filter:
    def __init__(self):
        self.name = None
        self.do_remove = True
        self.entries = []
        # we need project reference for dictionary list access
        self.proj = None

    def is_applicable(self, dt):
        for ln in self.entries:
            if isinstance(ln.column, ColumnDef):
                if not ln.column.does_present(dt.columns):
                    return False
            if isinstance(ln.value, ColumnDef):
                if not ln.value.does_present(dt.columns):
                    return False
        return True

    def uses_dict(self, dct):
        'does this filter use Dictionaty dct'
        for ln in self.entries:
            if isinstance(ln.column, ColumnDef):
                if ln.column.dict_name == dct.name:
                    return True
            if isinstance(ln.value, ColumnDef):
                if ln.value.dict_name == dct.name:
                    return True
        return False

    def change_dict_name(self, old, new):
        for e in self.entries:
            if isinstance(e.column, ColumnDef):
                if e.column.dict_name == old:
                    e.column.dict_name = new
            if isinstance(e.value, ColumnDef):
                if e.value.dict_name == old:
                    e.value.dict_name = new

    def copy_from(self, flt):
        self.proj = flt.proj
        self.name = flt.name
        self.do_remove = flt.do_remove
        self.entries = copy.deepcopy(flt.entries)

    def repr(self, column, value):
        dn = column.dict_name
        if dn is None or self.proj is None:
            return str(value)
        else:
            return self.proj.get_dictionary(dn).key_to_value(value)

    def to_singleline(self):
        ret = self.to_multiline()
        return ret.replace('\n', '')

    def to_multiline(self):
        ret2 = []
        for e in self.entries:
            ret = []
            if e is not self.entries[0]:
                ret.append(e.concat)
            ret.append(e.paren1)
            ret.append(e.column.name)
            ret.append(e.action)
            if isinstance(e.value, ColumnDef):
                ret.append(e.value.name)
            elif isinstance(e.value, list):
                ret.append(str(e.value))
            else:
                ret.append(self.repr(e.column, e.value))
            ret.append(e.paren2)
            ret2.append(" ".join(ret))
        ret3 = "\n".join(ret2)
        if not self.do_remove:
            ret3 = "NOT ({})".format(ret3)
        return ret3

    def to_sqlline(self, table):
        iparen = 0
        line = ""
        for e in self.entries:
            col1 = table.columns[e.column.name]
            col2 = None if not isinstance(e.value, ColumnDef) else\
                table.columns[e.value.name]
            ret = []
            # skip first
            if e is not self.entries[0]:
                ret.append(e.concat)
            # opening bracket
            ret.append(e.paren1)
            iparen += e.paren1.count('(')
            # first operand
            ret.append(col1.sql_line())
            # action
            if e.action == "==":
                ret.append("=")
            elif e.action in ["!=", ">", "<", ">=", "<="]:
                ret.append(e.action)
            elif e.action == "one of":
                ret.append("IN")
            elif e.action == "NULL":
                ret.append("IS NULL")
            elif e.action == "not NULL":
                ret.append("IS NOT NULL")
            else:
                raise NotImplementedError
            # second operand
            if e.action not in ["NULL", "not NULL"]:
                if col2 is not None:
                    ret.append(col2.sql_line())
                elif isinstance(e.value, list):
                    ret.append('(' + ", ".join(map(str, e.value)) + ')')
                else:
                    ret.append(str(e.value))
            # closing bracket
            if e.paren2 == ')...)':
                ret.append(')'*iparen)
                iparen = 0
            else:
                ret.append(e.paren2)
                iparen -= e.paren2.count(')')

            line += " ".join(ret)
        if self.do_remove:
            line = "NOT (" + line + ")"
        return line

    @classmethod
    def compile_sql_line(cls, filters, table):
        if len(filters) < 1:
            return ""
        else:
            r = ['(' + f.to_sqlline(table) + ')' for f in filters]
            return "WHERE " + " AND ".join(r)

    @classmethod
    def filter_by_values(cls, datatab, cnames, cvals, do_remove, use_and):
        ret = cls()
        ret.do_remove = do_remove
        for k, v in zip(cnames, cvals):
            e = FilterEntry()
            e.concat = "AND" if use_and else "OR"
            e.column = ColumnDef.from_column(datatab.columns[k])
            e.action = "=="
            e.value = v
            ret.entries.append(e)
        return ret

    @classmethod
    def filter_by_datalist(cls, datatab, cname, vals, do_remove):
        col = ColumnDef.from_column(datatab.columns[cname])
        if cname == 'id':
            ret = IdFilter()
        else:
            ret = Filter()
        ret.do_remove = do_remove
        if len(vals) == 0:
            return cls()
        if col.dt_type == "INT":
            IdFilter.set_from_ilist(ret, col, vals)
            return ret
        else:
            return cls.filter_by_values(datatab, [cname]*len(vals), vals,
                                        do_remove, do_remove)

    def add_conditions(self, f):
        if self.do_remove != f.do_remove:
            raise Exception("Cannot concatenate opposite filters")
        for e in f.entries:
            self.entries.append(copy.deepcopy(e))

    def to_xml(self, node, name=None):
        if name is None:
            name = self.name
        ET.SubElement(node, "NAME").text = escape(name)
        ET.SubElement(node, "DO_REMOVE").text = str(int(self.do_remove))
        for e in self.entries:
            e.to_xml(ET.SubElement(node, "E"))

    def to_xml_string(self, name=None):
        root = ET.Element("FILTER")
        self.to_xml(root, name)
        return ET.tostring(root, encoding='utf-8', method='xml').decode()

    @classmethod
    def from_xml(cls, node):
        ret = cls()
        ret.name = None
        if node.find('NAME').text is not None:
            ret.name = unescape(node.find('NAME').text)
        ret.do_remove = bool(int(node.find('DO_REMOVE').text))
        for nd in node.findall('E'):
            ret.entries.append(FilterEntry.from_xml(nd))
        return ret

    @classmethod
    def from_xml_string(cls, string):
        node = ET.fromstring(string)
        return cls.from_xml(node)


class ColumnDef:
    ' used to describe column in filter definition '
    def __init__(self, name, tp, dict_name):
        self.name = name
        self.dt_type = tp
        self.dict_name = dict_name

    def is_equal(self, coldef=None, column=None):
        if coldef is not None:
            return self.name == coldef.name and\
                   self.dt_type == coldef.dt_type and\
                   self.dict_name == coldef.dict_name
        elif column is not None:
            return self.is_equal(ColumnDef.from_column(column))
        else:
            return False

    def does_present(self, coldict):
        """ does this column present in column dictionary """
        try:
            col = coldict[self.name]
            if col.dt_type != self.dt_type:
                raise
            if not col.uses_dict(self.dict_name):
                raise
        except:
            return False
        else:
            return True

    def __str__(self):
        return str((self.name, self.dt_type, self.dict_name))

    @classmethod
    def from_column(cls, col):
        if not col.uses_dict(None):
            return cls(col.name, col.dt_type, col.repr_delegate.dict.name)
        else:
            return cls(col.name, col.dt_type, None)


class FilterEntry:
    def __init__(self):
        self.concat = "AND"
        self.paren1 = ""
        self.paren2 = ""
        self.column = None
        self.action = None
        self.value = None

    def to_xml(self, node):
        node.text = escape(str([self.concat,
                                self.paren1,
                                self.paren2,
                                str(self.column),
                                self.action,
                                self.value]))

    @classmethod
    def from_xml(cls, node):
        from ast import literal_eval

        ret = cls()
        [ret.concat,
         ret.paren1,
         ret.paren2,
         ret.column,
         ret.action,
         ret.value] = literal_eval(unescape(node.text))
        ret.column = ColumnDef(*literal_eval(ret.column))
        if isinstance(ret.value, str):
            try:
                ret.value = ColumnDef(*literal_eval(ret.value))
            except:
                pass
        return ret


class IdFilter(Filter):
    def __init__(self):
        super().__init__()

    def reset_id(self, used_ids):
        """ used ids should be sorted.
            returns false if no entries were left.
        """
        oldnew = {v: i+1 for i, v in enumerate(used_ids)}
        ret = []
        for x in self.unroll_data():
            try:
                ret.append(oldnew[x])
            except KeyError:
                break
        col = self.entries[0].column
        self.entries.clear()
        self.set_from_ilist(self, col)
        return len(self.entries) > 0

    @staticmethod
    def set_from_ilist(ret, col, ilist):
        slist = IdFilter.simplify_integer_list(ilist, 4)
        dist_ints = list(filter(lambda x: isinstance(x, int), slist))
        range_ints = list(filter(lambda x: isinstance(x, list), slist))
        # distinct integers
        if dist_ints:
            e = FilterEntry()
            e.column = col
            e.action = "one of"
            e.value = dist_ints
            ret.entries.append(e)
        # ranges
        for [r1, r2] in range_ints:
            e1, e2 = FilterEntry(), FilterEntry()
            e1.column = e2.column = col
            e1.concat = "OR"
            e2.concat = "AND"
            e1.paren1, e2.paren2 = '(', ')'
            e1.action, e2.action = ">=", "<="
            e1.value, e2.value = r1, r2
            ret.entries.extend([e1, e2])

    @staticmethod
    def simplify_integer_list(ilist, minrange):
        """ (1,2,3,4,5, 8, 12,13,14) -> [1,5], 8, [12,14]
        """
        srt = sorted(set(ilist))
        if len(ilist) == 0:
            return []
        ret = []
        i, istart = 0, 0
        while i < len(srt):
            while i < len(srt) and srt[i] - srt[istart] == i - istart:
                i += 1
            if i - istart >= minrange:
                ret.append([srt[istart], srt[i-1]])
            else:
                ret.extend(srt[istart:i])
            istart = i
        return ret
