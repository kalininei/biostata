import numpy as np


def population_covariance_matrix(mat):
    return np.cov(mat, bias=True)

def sample_covariance_matrix(mat):
    return np.cov(mat, bias=False)

def correlation_matrix(mat):
    return np.corrcoef(mat)
