import numpy as np
from prog import filt


def mat_raw_values(dt, colnames):
    colslist = [dt.get_column(x) for x in colnames]
    flt = [dt.get_filter(iden=x) for x in dt.used_filters]
    # add not NULL filters
    for c in colnames:
        flt.append(filt.filter_nonnull(dt, c))
    qr = dt._compile_query(colslist, filters=flt,
                           status_adds=False, group_adds=False)
    dt.query(qr)
    return np.array(dt.qresults()).transpose()
