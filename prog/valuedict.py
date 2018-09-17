import collections


class Dictionary:
    def __init__(self, name, dt_type, keys, values, comments=None):
        if dt_type not in ["BOOL", "ENUM"]:
            raise Exception("Invalid dictionary data type")

        if keys is None:
            keys = list(range(len(values)))

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

    def compare(self, newdict):
        """ What was changed in newdict compared to present dict.
            Returns list of possible entries:
            ['name', 'keys added', 'keys removed', 'values changed',
             'comments changed']
        """
        ret = []
        if self.name != newdict.name:
            ret.append('name')
        if len(set(self.keys()).difference(newdict.keys())) > 0:
            ret.append('keys removed')
        if len(set(newdict.keys()).difference(self.keys())) > 0:
            ret.append('keys added')
        for k, v in self.kvalues.items():
            if k in newdict.kvalues:
                if v != newdict.kvalues[k]:
                    ret.append('values changed')
                    break
        for k, v in self.kcomments.items():
            if k in newdict.kcomments:
                if v != newdict.kcomments[k]:
                    ret.append('comments changed')
                    break
        return ret

    def copy_from(self, dct):
        self.dt_type = dct.dt_type
        self.name = dct.name
        self.kvalues.clear()
        for k, v in dct.kvalues.items():
            self.kvalues[k] = v
        self.vkeys.clear()
        for k, v in dct.vkeys.items():
            self.vkeys[k] = v
        self.kcomments.clear()
        for k, v in dct.kcomments.items():
            self.kcomments[k] = v

    def count(self):
        return len(self.kvalues)

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

    def comments(self):
        return list(self.kcomments.values())

    def keys_to_str(self):
        return str(self.keys())

    def values_to_str(self):
        return str(self.values())

    def comments_to_str(self):
        return str(list(self.kcomments.values()))

    @staticmethod
    def from_db(name, proj):
        import ast
        qr = """
            SELECT "type", "keys", "values", "comments" FROM A._DICTIONARIES_
            WHERE name='{}' """.format(name)
        proj.sql.query(qr)
        f = proj.sql.qresult()
        dt_type = f[0]

        keys = ast.literal_eval(f[1])
        values = ast.literal_eval(f[2])
        comments = ast.literal_eval(f[3])

        return Dictionary(name, dt_type, keys, values, comments)


dict_az = Dictionary('A-Z', 'ENUM', None, list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
dict_09 = Dictionary('0-9', 'ENUM', None, list('0123456789'))
dict_01 = Dictionary('0-1', 'BOOL', None, list('01'))
dict_truefalse = Dictionary('True/False', 'BOOL', None, ['False', 'True'])
dict_yesno = Dictionary('Yes/No', 'BOOL', None, ['No', 'Yes'])
