import copy


def possible_values_list(column, operation, datatab):
    ret = []

    def append_col_names(tp):
        for c in datatab.columns.values():
            if c is not column and c.dt_type == tp:
                ret.append('"{}"'.format(c.name))

    if column.dt_type == "INTEGER" and operation != "one of":
        append_col_names("INTEGER")
    elif column.dt_type == "REAL":
        append_col_names("REAL")
    elif column.dt_type == "ENUM":
        ret.extend(column.possible_values_short.values())
    elif column.dt_type == "BOOLEAN":
        ret.append(column.possible_values_short[0] + " (False)")
        ret.append(column.possible_values_short[1] + " (True) ")
        append_col_names("BOOLEAN")
    else:
        raise NotImplementedError
    return ret


def factions(dt_type):
    a0 = ["==", "!="]
    ae = ["NULL", "not NULL"]
    a1 = [">", "<", ">=", "<="]
    if dt_type == "INTEGER":
        a = a1 + ["one of"]
    elif dt_type == "REAL":
        a = a1
    elif dt_type == "BOOLEAN":
        a = []
    elif dt_type == "ENUM":
        a = []
    else:
        raise NotImplementedError
    return copy.deepcopy(a0 + a + ae)

fconcat = ["AND", "OR", "AND NOT", "OR NOT"]

fopenparen = ["", "(", "( (", "( ( ("]

fcloseparen = ["", ")", ") )", ") ) )", ")...)"]


class Filter:
    def __init__(self):
        self.name = None
        self.do_remove = True
        self.entries = []

    def is_applicable(self, dt):
        from bdata import dtab
        for ln in self.entries:
            if isinstance(ln.column, dtab.ColumnInfo):
                if ln.column.name not in dt.columns:
                    return False
            if isinstance(ln.value, dtab.ColumnInfo):
                if ln.value.name not in dt.columns:
                    return False
        return True

    def copy_from(self, flt):
        self.name = flt.name
        self.entries = [FilterEntry() for _ in flt.entries]
        for l1, l2 in zip(self.entries, flt.entries):
            l1.copyfrom(l2)

    def to_singleline(self):
        ret = self.to_multiline()
        return ret.replace('\n', '')

    def to_multiline(self):
        from bdata import dtab
        ret2 = []
        for e in self.entries:
            ret = []
            if e is not self.entries[0]:
                ret.append(e.concat)
            ret.append(e.paren1)
            ret.append(e.column.name)
            ret.append(e.action)
            if isinstance(e.value, dtab.ColumnInfo):
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
