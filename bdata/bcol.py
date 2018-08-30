import copy


# -------------------- Column information
class ColumnInfo:
    def __init__(self):
        self.name = None
        self.shortname = None
        self.is_original = None
        self.is_category = None
        self.dt_type = None
        self.sql_group_fun = None
        self.sql_fun = None
        self.sql_data_type = None
        self._long_caption = None
        self.status_column = None
        # this is not None only for enum and boolean types
        self.possible_values = None
        # defined delegates
        self._assign_representation_funs()

    def short_caption(self):
        return self.shortname

    def long_caption(self):
        return self._long_caption

    def _build_status_column(self):
        ret = ColumnInfo()
        if self.is_original:
            ret.name = ret.shortname = '_status_' + self.name
            ret.sql_fun = '"{}"'.format(ret.name)
        else:
            # fake status column filled with zeros
            ret.name = ret.shortname = ret.sql_fun = '0'
        ret.is_original = False
        ret.is_category = False
        ret.sql_group_fun = 'MAX({})'.format(ret.sql_fun)
        ret.sql_data_type = "INTEGER"
        ret.dt_type = "BOOLEAN"
        self.status_column = ret

    def _assign_representation_funs(self):
        self.repr = lambda x: "" if x is None else x
        self.from_repr = lambda x: None if x == "" else x

        if self.dt_type in ["ENUM", "BOOLEAN"]:
            self.repr = lambda x: "" if x is None else\
                    self.possible_values[x]
            self.from_repr = lambda x: None if x == "" else next(
                k for k, v in self.possible_values.items() if v == x)

    # --------------- constructors
    def build_deep_copy(self, newname=None):
        """ copies, breaks all dependencies """
        ret = ColumnInfo()
        ret.name = self.name if newname is None else newname
        ret.shortname = self.shortname
        ret.is_original = True
        ret.is_category = self.is_category
        ret.dt_type = self.dt_type
        ret.sql_fun = '"{}"'.format(ret.name)
        pos = self.sql_group_fun.find('(')
        ret.sql_group_fun = "{}({})".format(
                self.sql_group_fun[:pos], ret.sql_fun)
        ret.sql_data_type = self.sql_data_type
        ret._long_caption = ret.name
        ret.possible_values = copy.deepcopy(self.possible_values)
        ret._assign_representation_funs()
        ret._build_status_column()
        return ret

    @classmethod
    def build_from_category(cls, category):
        ret = cls()
        ret.name = category.name
        ret.shortname = category.shortname
        ret.is_original = True
        ret.is_category = category.is_category
        ret.sql_fun = '"' + ret.name + '"'
        if ret.is_category:
            ret.sql_group_fun = 'category_group({})'.format(ret.sql_fun)
        else:
            ret.sql_group_fun = 'AVG({})'.format(ret.sql_fun)
        ret.dt_type = category.dt_type
        if category.dt_type != "REAL":
            ret.sql_data_type = "INTEGER"
        else:
            ret.sql_data_type = "REAL"
        if category.dim:
            ret._long_caption = "{0}".format(ret.name, category.dim)
        else:
            ret._long_caption = ret.name

        ret.possible_values = category.possible_values

        # changing representation function for boolean and enum types
        ret._assign_representation_funs()
        ret._build_status_column()
        return ret

    @classmethod
    def build_bool_category(cls, name, shortname, yesno, sql_fun=None):
        ret = cls()
        ret.name = name
        ret.shortname = shortname
        ret._long_caption = name
        if sql_fun is None:
            ret.is_original = True
            ret.sql_fun = '"{}"'.format(name)
        else:
            ret.is_original = False
            ret.sql_fun = sql_fun
        ret.is_category = True
        ret.dt_type = "BOOLEAN"
        ret.sql_group_fun = 'category_group({})'.format(ret.sql_fun)
        ret.sql_data_type = "INTEGER"
        ret.possible_values = {0: yesno[1], 1: yesno[0]}
        ret._assign_representation_funs()
        ret._build_status_column()
        return ret

    @classmethod
    def build_enum_category(cls, name, shortname, posvals, sql_fun=None):
        ret = cls()
        ret.name = name
        ret.shortname = shortname
        ret._long_caption = name
        ret.is_original = False
        if sql_fun is None:
            ret.is_original = True
            ret.sql_fun = '"{}"'.format(name)
        else:
            ret.is_original = False
            ret.sql_fun = sql_fun
        ret.is_category = True
        ret.dt_type = "ENUM"
        ret.sql_group_fun = 'category_group({})'.format(ret.sql_fun)
        ret.sql_data_type = "INTEGER"
        ret.possible_values = {k+1: v for k, v in enumerate(posvals)}
        ret._assign_representation_funs()
        ret._build_status_column()
        return ret

    @classmethod
    def build_id_category(cls):
        ret = cls()
        ret.name = 'id'
        ret.shortname = 'id'
        ret.is_original = True
        ret.is_category = True
        ret.dt_type = "INTEGER"
        ret.sql_group_fun = 'category_group(id)'
        ret.sql_fun = '"id"'
        ret.sql_data_type = "INTEGER"
        ret._long_caption = "id"
        ret._build_status_column()
        return ret


class DerivedColumnInfo(ColumnInfo):
    def __init__(self, deps):
        super().__init__()
        self.dependencies = deps


class CollapsedCategories(DerivedColumnInfo):
    def __init__(self, categories):
        super().__init__(categories)
        self.name = '-'.join([c.shortname for c in categories])
        self.shortname = self.name
        self.is_original = False
        self.is_category = True
        self.dt_type = "TEXT"
        self.sql_fun = 'category_merge({})'.format(
                ', '.join([c.sql_fun for c in categories]))
        self.sql_group_fun = "merged_group({})".format(
                ', '.join([c.sql_fun for c in categories]))
        self.sql_data_type = "TEXT"
        self._long_caption = self.name
        self._build_status_column()
        self.delimiter = '-'

        # representation
        def r(x):
            sp = x.split(' & ')
            ret = []
            for c, x in zip(self.dependencies, sp):
                try:
                    if c.dt_type != "BOOLEAN":
                            ret.append(c.repr(int(x)))
                    else:
                        ret.append(c.possible_values[int(x)])
                except ValueError:
                    ret.append(x)
            return self.delimiter.join(map(str, ret))

        self.repr = r
        self.rrepr = None

    def _build_status_column(self):
        super()._build_status_column()
        self.status_column.sql_fun = 'max_per_list({})'.format(
            ','.join([x.status_column.sql_fun for x in self.dependencies]))

    class InvalidDeepCopy(Exception):
        def __init__(self):
            super().__init__("Can not build a copy of collapsed categories")

    def build_deep_copy(self, col):
        # Use conversation to enum column instead
        raise CollapsedCategories.InvalidDeepCopy()
