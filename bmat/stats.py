import numpy as np
import scipy
import scipy.stats
from bmat import npinterface


def population_covariance_matrix(mat):
    return np.cov(mat, bias=True)


def sample_covariance_matrix(mat):
    return np.cov(mat, bias=False)


def correlation_matrix(mat):
    return np.corrcoef(mat)


def linear_regression(x, y):
    """ f = a*x + b,
        returns a, b, stderr, slopeerr, corr. coeff
    """
    if np.size(x) < 2:
        return (None,)*5
    r = scipy.stats.linregress(x, y)
    xr = scipy.polyval([r.slope, r.intercept], x)
    err = np.sqrt(np.sum((xr - y)**2)/np.size(x))
    return r.slope, r.intercept, err, r.stderr, r.rvalue


def log_regression(xin, yin):
    """ f = a*ln(x) + b,
        returns a, b, stderr, slopeerr, corr. coeff
    """
    x, y = xin[xin > 0], yin[xin > 0]
    if np.size(x) < 2:
        return (None,)*5
    logx = np.log(x)
    r = scipy.stats.linregress(logx, y)
    xr = scipy.polyval([r.slope, r.intercept], logx)
    err = np.sqrt(np.sum((xr - y)**2)/np.size(x))
    return r.slope, r.intercept, err, r.stderr, r.rvalue


def power_regression(xin, yin):
    """ f = b*(x^a)
        returns a, b, stderr, slopeerr, corr. coeff
    """
    minxy = np.array([xin, yin]).min(axis=0)
    x, y = xin[minxy > 0], yin[minxy > 0]
    if np.size(x) < 2:
        return (None,)*5
    logx, logy = np.log(x), np.log(y)
    r = scipy.stats.linregress(logx, logy)
    a = r.slope
    b = np.exp(r.intercept)
    xr = b*(x**a)
    err = np.sqrt(sum((xr - y)**2)/np.size(x))
    return a, b, err, r.stderr, r.rvalue


def hierarchical_linkage(mat, method):
    import scipy.cluster.hierarchy as sch
    if method == 'Ward':
        m = 'ward'
    elif method == 'Nearest Point':
        m = 'single'
    elif method == 'Farthest Point':
        m = 'complete'
    elif method == 'Centroid':
        m = 'centroid'
    return sch.linkage(mat, method=m, optimal_ordering=True)


class HierarchicalLinkage:
    def __init__(self, dt, colnames, method):
        self.dt = dt
        self.colnames = colnames
        self._used_method = None
        if method is not None:
            self.recalc(method)

    def recalc(self, method):
        if self._used_method == method:
            return
        self._used_method = method
        self.mat, self.rowid = npinterface.mat_raw_values(
                self.dt, self.colnames, cols_to_rows=False, rowind=True)
        self.linkage = hierarchical_linkage(self.mat, method)

        self.bottom_order = self._build_bottom_order()
        self._group_samples = [None] * (2 * self.samp_count() - 1)
        self._root_groups = [None] * (self.samp_count() + 1)

    def was_calculated(self):
        return self._used_method is not None

    def samp_count(self):
        return np.size(self.rowid)

    def groups_count(self):
        return 2 * np.size(self.rowid) - 1

    def source_count(self):
        return len(self.colnames)

    def get_group_distance(self, ig):
        if ig < self.samp_count():
            return 0.0
        else:
            return self.linkage[ig - self.samp_count(), 2]

    def get_group_samples(self, ig):
        """ returns array of lowest groups for specified group id
            ig - zero based group index
        """
        if self._group_samples[ig] is None:
            self._group_samples[ig] = self._calculate_group_samples(ig)
        return self._group_samples[ig]

    def _calculate_group_samples(self, ig):
        if ig < np.size(self.rowid):
            return np.array([ig])
        leftg = int(self.linkage[ig - self.samp_count(), 0])
        rightg = int(self.linkage[ig - self.samp_count(), 1])
        left = self.get_group_samples(leftg)
        right = self.get_group_samples(rightg)
        return np.concatenate((left, right))

    def get_root_groups(self, ngroups):
        """ returns root groups ids for specified number of groups
        """
        if self._root_groups[ngroups] is None:
            self._root_groups[ngroups] = self._calculate_root_groups(ngroups)
        return self._root_groups[ngroups]

    def _calculate_root_groups(self, ngroups):
        if ngroups == 1:
            return np.array([self.groups_count() - 1])
        elif ngroups == self.samp_count():
            return np.array(self.bottom_order)
        else:
            ng = self.get_root_groups(ngroups - 1)
            besty = -1
            cand = None
            for r in np.nditer(ng[ng >= self.samp_count()]):
                if self.get_group_distance(r) > besty:
                    besty = self.get_group_distance(r)
                    cand = r
            assert cand is not None
            li = cand - self.samp_count()
            ret = np.concatenate((ng[ng != cand],
                                  self.linkage[li, 0:2].astype(int)))
            return np.sort(ret)

    def max_distance(self):
        return np.max(self.linkage[:, 2])

    def _build_bottom_order(self):
        'returns permutation of range(samp_count())'
        def place_items(lnk, sz, left, right, ret):
            left, right = int(left), int(right)
            if left < sz:
                ret.append(left)
            else:
                l, r = lnk[left-sz, 0], lnk[left-sz, 1]
                place_items(lnk, sz, l, r, ret)
            if right < sz:
                ret.append(right)
            else:
                l, r = lnk[right-sz, 0], lnk[right-sz, 1]
                place_items(lnk, sz, l, r, ret)

        st = np.argmax(self.linkage[:, 3])
        ret = []
        place_items(self.linkage, self.samp_count(), self.linkage[st, 0],
                    self.linkage[st, 1], ret)
        return np.array(ret)

    def group_mean_std(self, ig):
        ir = self.get_group_samples(ig)
        return self.mat[ir, :].std(axis=0).mean()

    def column_group_mean(self, ig, icol):
        ir = self.get_group_samples(ig)
        return self.mat[ir, icol].mean()

    def column_group_std(self, ig, icol):
        ir = self.get_group_samples(ig)
        return self.mat[ir, icol].std()

    def column_group_min(self, ig, icol):
        ir = self.get_group_samples(ig)
        return self.mat[ir, icol].min()

    def column_group_max(self, ig, icol):
        ir = self.get_group_samples(ig)
        return self.mat[ir, icol].max()
