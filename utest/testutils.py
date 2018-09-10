from PyQt5 import QtCore


def print_dtab(dt):

    for i in range(dt.n_rows()):
        line = []
        for j in range(dt.n_cols()):
            v = dt.get_value(i, j)
            if v is None:
                v = '<None>'
            line.append("{0: >8}".format(v))
        print(''.join(line))


def get_dtab_column(dt, icol):
    ret = []
    for i in range(dt.n_rows()):
        ret.append(dt.get_value(i, icol))
    return ret


def get_dtab_raw_column(dt, icol):
    ret = []
    for i in range(dt.n_rows()):
        ret.append(dt.get_raw_value(i, icol))
    return ret


def get_tmodel_column(tm, icol):
    ret = []
    for i in range(2, tm.rowCount()):
        index = tm.createIndex(i, icol)
        dt = tm.data(index, QtCore.Qt.DisplayRole)
        ret.append(dt)
    return ret


def get_tmodel_raw_column(tm, icol):
    from bgui import tmodel
    ret = []
    for i in range(2, tm.rowCount()):
        index = tm.createIndex(i, icol)
        dt = tm.data(index, tmodel.TabModel.RawValueRole)
        ret.append(dt)
    return ret
