import numpy as np


def mat_raw_values(dt, colnames):
    ''' returns 2D array where each row contains defined dt column.
        dt rows which contain any None value are ignored.
    '''
    colslist = [dt.get_column(x) for x in colnames]
    qr = dt._compile_query(colslist, status_adds=False, group_adds=False)
    dt.query(qr)
    ret = np.array(dt.qresults())
    # remove rows which contain None values
    notnone = np.all(ret != np.array(None), axis=1)
    return ret[notnone].transpose()
