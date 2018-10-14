import numpy as np
import base64


def mat_raw_values(dt, colnames, cols_to_rows=True, rowind=False):
    ''' returns 2D array where each row contains defined dt column.
        dt rows which contain any None value are ignored.
        If rowind => forces output of visible row index.
        It differs from range() if None values present.
    '''
    colslist = [dt.get_column(x) for x in colnames]
    qr = dt._compile_query(colslist, status_adds=False, group_adds=False)
    dt.query(qr)
    ret = np.array(dt.qresults())
    # remove rows which contain None values
    notnone = np.all(ret != np.array(None), axis=1)

    if rowind:
        if cols_to_rows:
            return ret[notnone].transpose(), np.where(notnone)[0] + 1
        else:
            return ret[notnone], np.where(notnone)[0] + 1
    else:
        if cols_to_rows:
            return ret[notnone].transpose()
        else:
            return ret[notnone]


def serialize_array(a):
    assert isinstance(a, np.ndarray)
    assert a.dtype.name in ['int64', 'float64']
    ret = {}
    ret['shape'] = np.shape(a)
    s = base64.b64encode(a.tostring()).decode('utf-8')
    ret['data'] = s
    ret['tp'] = a.dtype.name
    return ret


def is_serialized_array(v):
    if isinstance(v, dict) and 'shape' in v and 'data' in v and 'tp' in v:
        return True
    else:
        return False


def unserialize_array(a):
    s = base64.b64decode(a['data'])
    ret = np.fromstring(s, a['tp'])
    return ret.reshape(a['shape'])
