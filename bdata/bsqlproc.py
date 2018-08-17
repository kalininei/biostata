def group_repr(c):
    """ c -> ...[c] """
    return '...[' + str(c) + ']'

tech_splitter = ' & '


class _Grouping1:
    def __init__(self):
        self.vals = []

    def step(self, v):
        self.vals.append(v)


class _GroupingA:
    def __init__(self):
        self.vals = []

    def step(self, *args):
        self.vals.append([v for v in args if v is not None])


class CategoryGrouping(_Grouping1):
    """ If all processed values are equal returns it,
        Otherwise returns None
    """
    def __init__(self):
        super().__init__()

    def finalize(self):
        s = set(self.vals)
        if len(s) == 1:
            return self.vals[0]
        else:
            return None


class MergedCategoryGrouping(_GroupingA):
    def __init__(self):
        super().__init__()

    def finalize(self):
        if not self.vals:
            return None
        cols = []
        for i in range(len(self.vals[0])):
            c = set([x[i] for x in self.vals])
            if len(c) == 1:
                cols.append(str(self.vals[0][i]))
            else:
                cols.append(group_repr(len(c)))
        return tech_splitter.join(cols)


class MedianDataGrouping(_Grouping1):
    def __init__(self):
        super().__init__()

    def finalize(self):
        if not self.vals:
            return None
        indp = int(len(self.vals)/2)
        s = sorted(self.vals)
        if len(self.vals) % 2 == 0:
            return (s[indp] + s[indp-1])/2
        else:
            return s[indp]


class MedianPDataGrouping(_Grouping1):
    def __init__(self):
        super().__init__()

    def finalize(self):
        if not self.vals:
            return None
        indp = int(len(self.vals)/2)
        s = sorted(self.vals)
        return s[indp]


class MedianMDataGrouping(_Grouping1):
    def __init__(self):
        super().__init__()

    def finalize(self):
        if not self.vals:
            return None
        indp = int(len(self.vals)/2)
        s = sorted(self.vals)
        return s[indp-1]


def category_merge(*args):
    return tech_splitter.join(map(str, args))


def max_per_list(*args):
    return max(args)

# those functions will be added to each connection passed to TabModel
registered_aggregate_functions = [
        ("category_group", 1, CategoryGrouping),
        ("merged_group", -1, MergedCategoryGrouping),
        ("median", 1, MedianDataGrouping),
        ("medianp", 1, MedianPDataGrouping),
        ("medianm", 1, MedianMDataGrouping),
]
registered_sql_functions = [
        ("category_merge", -1, category_merge),
        ("max_per_list", -1, max_per_list),
]


def init_connection(connection):
    for r in registered_aggregate_functions:
        connection.create_aggregate(*r)
    for r in registered_sql_functions:
        connection.create_function(*r)
