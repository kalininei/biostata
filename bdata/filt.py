import copy
from bdata import bcol


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
        ret.extend(column.dict.possible_values.values())
    elif column.dt_type == "BOOL":
        ret.append(column.dict.possible_values[0] + " (False)")
        ret.append(column.dict.possible_values[1] + " (True) ")
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

    def is_applicable(self, dt):
        for ln in self.entries:
            if isinstance(ln.column, bcol.ColumnInfo):
                if ln.column.name not in dt.columns:
                    return False
            if isinstance(ln.value, bcol.ColumnInfo):
                if ln.value.name not in dt.columns:
                    return False
        return True

    def copy_from(self, flt):
        self.name = flt.name
        self.do_remove = flt.do_remove
        self.entries = [FilterEntry() for _ in flt.entries]
        for l1, l2 in zip(self.entries, flt.entries):
            l1.copyfrom(l2)

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
            if isinstance(e.value, bcol.ColumnInfo):
                ret.append(e.value.name)
            elif isinstance(e.value, list):
                ret.append(str(e.value))
            else:
                ret.append(str(e.column.repr(e.value)))
            ret.append(e.paren2)
            ret2.append(" ".join(ret))
        ret3 = "\n".join(ret2)
        if not self.do_remove:
            ret3 = "NOT ({})".format(ret3)
        return ret3

    def to_sqlline(self):
        iparen = 0
        line = ""
        for e in self.entries:
            ret = []
            if e is not self.entries[0]:
                ret.append(e.concat)
            # opening bracket
            ret.append(e.paren1)
            iparen += e.paren1.count('(')
            # first operand
            ret.append(e.column.sql_line())
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
                if isinstance(e.value, bcol.ColumnInfo):
                    ret.append(e.value.sql_line())
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
    def compile_sql_line(cls, filters):
        if len(filters) < 1:
            return ""
        else:
            r = ['(' + f.to_sqlline() + ')' for f in filters]
            return "WHERE " + " AND ".join(r)

    @classmethod
    def filter_by_values(cls, datatab, cnames, cvals, do_remove, use_and):
        ret = cls()
        ret.do_remove = do_remove
        for k, v in zip(cnames, cvals):
            e = FilterEntry()
            e.concat = "AND" if use_and else "OR"
            e.column = datatab.columns[k]
            e.action = "=="
            e.value = v
            ret.entries.append(e)
        return ret

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

    @classmethod
    def filter_by_datalist(cls, datatab, cname, vals, do_remove):
        ret = cls()
        ret.do_remove = do_remove
        col = datatab.columns[cname]
        if len(vals) == 0:
            return cls()
        if col.dt_type == "INT":
            slist = cls.simplify_integer_list(vals, 4)
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
            return ret
        else:
            return cls.filter_by_values(datatab, [cname]*len(vals), vals,
                                        do_remove, do_remove)

    def add_conditions(self, f):
        if self.do_remove != f.do_remove:
            raise Exception("Cannot concatenate opposite filters")
        for e in f.entries:
            self.entries.append(FilterEntry())
            self.entries[-1].copyfrom(e)


class FilterEntry:
    def __init__(self):
        self.concat = "AND"
        self.paren1 = ""
        self.paren2 = ""
        self.column = None
        self.action = None
        self.value = None

    def copyfrom(self, flt):
        # avoiding deepcopy to prevent deepcopy of ColumnInfo
        self.concat = flt.concat
        self.paren1 = flt.paren1
        self.paren2 = flt.paren2
        self.column = flt.column
        self.action = flt.action
        self.value = flt.value
