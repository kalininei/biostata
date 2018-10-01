import numpy as np
import scipy
import scipy.stats


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
