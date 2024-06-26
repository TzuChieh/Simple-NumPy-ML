import common.vector as vec

import numpy as np
import pytest


@pytest.mark.parametrize(
    "matrix_shape, kernel_shape, stride_shape, expected", [
    ((2, 2),       (1, 1),       (1, 1),       (2, 2)),
    ((1, 1),       (1, 1),       (1, 1),       (1, 1)),
    ((1, 1),       (1, 1),       (777, 1),     (1, 1)),
    ((1, 1),       (1, 1),       (2, 2),       (1, 1)),
    ((3, 3),       (2, 2),       (1, 1),       (2, 2)),
    ((4, 5),       (3, 2),       (1, 1),       (2, 4)),
    ((5, 5),       (1, 2),       (2, 1),       (3, 4)),
    ((6, 8),       (3, 3),       (2, 3),       (2, 2)),
])
def test_correlate_shape_2d(matrix_shape, kernel_shape, stride_shape, expected):
    result = vec.correlate_shape(matrix_shape, kernel_shape, stride_shape)
    assert np.array_equal(result, expected)
    
@pytest.mark.parametrize(
    "matrix_shape, stride_shape", [
    ((2, 2),       (1, 1)),
    ((1, 1),       (1, 1)),
])
def test_correlate_shape_2d_matrix_smaller_than_kernel(matrix_shape, stride_shape):
    """
    Since matrix is smaller than kernel, resulting shapes should always be 0.
    """
    my, mx = matrix_shape
    for ky in range(my + 1, my + 10):
        for kx in range(mx + 1, mx + 10):
            kernel_shape = (ky, kx)
            result = vec.correlate_shape(matrix_shape, kernel_shape, stride_shape)
            assert np.array_equal(result, (0, 0))
    
@pytest.mark.parametrize(
    "matrix_shape,   kernel_shape, stride_shape, expected", [
    ((123, 5, 5),    (1, 2),       (2, 1),       (123, 3, 4)),
    ((55, 66, 6, 8), (3, 3),       (2, 3),       (55, 66, 2, 2)),
])
def test_correlate_shape_nd(matrix_shape, kernel_shape, stride_shape, expected):
    result = vec.correlate_shape(matrix_shape, kernel_shape, stride_shape)
    assert np.array_equal(result, expected)
    
@pytest.mark.parametrize(
    "matrix, kernel, stride_shape, expected", [
    (np.full((3, 3), 1), np.full((1, 1), 1), (1, 1), np.full((3, 3), 1)),
    (np.full((3, 3), 1), np.full((2, 2), 1), (1, 1), np.full((2, 2), 4)),
    (np.full((2, 3), 1), np.full((2, 2), 1), (1, 1), np.full((1, 2), 4)),
    (np.full((3, 4), 1), np.full((2, 3), 1), (1, 1), np.full((2, 2), 6)),
    (np.full((3, 4), 1), np.full((2, 3), 1), (1, 2), np.full((2, 1), 6)),
    (np.full((2, 4), 1), np.full((2, 2), 1), (123, 2), np.full((1, 2), 4)),
    (np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), np.array([[-1, -2]]), (2, 1), np.array([[-5, -8], [-23, -26]])),
])
def test_correlate_2d(matrix, kernel, stride_shape, expected):
    result = vec.correlate(matrix, kernel, stride_shape)
    assert np.array_equal(result, expected)
    
@pytest.mark.parametrize(
    "matrix, kernel, stride_shape, expected", [
    (np.full((2, 2), 1), np.full((3, 3), 1), (1, 1), np.full((0, 0), 1)),
    (np.full((2, 2), 1), np.full((5, 5), 1), (1, 1), np.full((0, 0), 1)),
    (np.full((1, 1), 1), np.full((10, 10), 1), (1, 1), np.full((0, 0), 1)),
])
def test_correlate_2d_matrix_smaller_than_kernel(matrix, kernel, stride_shape, expected):
    """
    Since matrix is smaller than kernel, resulting shapes should always be 0.
    """
    result = vec.correlate(matrix, kernel, stride_shape)
    assert np.array_equal(result, expected)
    