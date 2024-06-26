import common as com

import numpy as np
import numpy.typing as np_type


def _make_kernel_dim_to_einsum_correlation_expr():
    chars = 'abcdefghijklmnopqrstuvwxyz'
    result = {}
    for dim in range(1, 26 + 1):
        # Builds the expression for current dimension, e.g., for `dim == 2`, `result[dim] == '...ab,...ab->...'`
        subscripts = chars[:dim]
        result[dim] = f'...{subscripts},...{subscripts}->...'
    return result

_kernel_dim_to_einsum_correlation_expr = _make_kernel_dim_to_einsum_correlation_expr()


def is_vector_2d(m: np_type.NDArray) -> bool:
    """
    @return Whether the last two dimensions of the matrix is a column vector.
    """
    return len(m.shape) >= 2 and m.shape[-1] == 1

def zeros_from(m: np_type.NDArray) -> np_type.NDArray:
    """
    Same as `numpy.zeros()`, except that settings are inferred from `m`.
    """
    return np.zeros(m.shape, dtype=m.dtype)

def vector_2d(m: np_type.NDArray) -> np_type.NDArray:
    """
    Reshape the last two dimensions of the matrix into a column vector. Other dimensions remain unchanged.
    @param m The matrix to reshape into vector.
    """
    length = np.prod(m.shape[-2:])
    return m.reshape((*m.shape[:-2], length, 1))

def transpose_2d(m: np_type.NDArray) -> np_type.NDArray:
    """
    Transpose the last two dimensions of a matrix. Other dimensions remain unchanged.
    @param m The matrix to transpose.
    """
    return np.swapaxes(m, -2, -1)

def diag_from_vector_2d(m: np_type.NDArray) -> np_type.NDArray:
    """
    Create diagonal matrices from column vectors (the last two dimensions of a matrix). Other dimensions
    remain unchanged.
    """
    assert is_vector_2d(m), f"`m` must be column vectors (shape: {m.shape})"

    # Column vector elements are along axis=-2, use them to create diagonal matrices
    diag = np.apply_along_axis(np.diagflat, -2, m)

    # Remove the redundant 1-wide x axis (originally for the column vector)
    diag = diag[..., 0]

    assert len(diag.shape) == len(m.shape), f"shapes: {diag.shape}, {m.shape}"
    return diag

def reshape_lower(a: np_type.NDArray, shape) -> np_type.NDArray:
    """
    Reshape the lower dimensions of an array while keeping higher dimensions intact.
    @param a The array to reshape.
    @param shape The lower dimensions to reshape into. `a.shape[0]` is the highest dimension and `a.shape[-1]` is
    the lowest dimension.
    @return A reshaped `a` with matching lower dimensions, while higher dimensions (if any) are kept. For example,
    an array `a` of shape (3, 2, 1) will be reshaped into (3, 1, 2) after `a = reshape_lower(a, (1, 2))`.
    """
    return a.reshape((*a.shape[:-len(shape)], *shape))

def argmax_lower(a: np_type.NDArray, num_dims) -> np_type.NDArray:
    """
    Similar to `numpy.argmax()`, except this helper works on lower dimensions of an array and returns non-flat
    indices suitable for use with NumPy advanced indexing.
    @param a The array to perform argmax.
    @param num_dims Number of lower dimensions to perform argmax in. `a.shape[0]` is the highest dimension and
    `a.shape[-1]` is the lowest dimension.
    @return Tuple of array of indices into the last `num_dims` dimensions of `a`, where each index corresponds to the
    maximum element found. The tuple is suitable for use with NumPy advanced indexing to retrieve the actual values:
    ```python
    >>> a = np.array([[1, 2, 3], [4, 5, 6]])
    >>> a[[0, 1], *argmax_lower(a, 1)]
    [3, 6]
    ```
    """
    higher_shape = a.shape[:-num_dims]
    lower_shape = a.shape[-num_dims:]
    lower_flattened_a = a.reshape((*higher_shape, np.prod(lower_shape)))
    max_flat_indices = lower_flattened_a.argmax(axis=-1)
    return np.unravel_index(max_flat_indices, lower_shape)

def correlate_shape(matrix_shape, kernel_shape, stride_shape=(1,)) -> np_type.NDArray:
    """
    Given the shapes, computes the resulting shape after the correlation. Will compute with the kernel's dimensions
    (other dimensions remain unchanged).
    @param kernel_shape Kernel dimensions.
    @param stride_shape Stride dimensions (for moving the kernel).
    """
    assert len(matrix_shape) >= len(kernel_shape)

    nd = len(kernel_shape)
    stride_shape = np.broadcast_to(stride_shape, nd)
    correlate_size = np.floor_divide(np.subtract(matrix_shape[-nd:], kernel_shape), stride_shape) + 1

    # Could be negative if kernel is smaller than matrix, clamp it
    correlate_size = np.maximum(correlate_size, 0)

    return (*matrix_shape[:-nd], *correlate_size)

def dilate_shape(matrix_shape, stride_shape, pad_shape=(0,)) -> np_type.NDArray:
    """
    Given the shapes, computes the resulting shape after the dilation. Will compute with the stride's and pad's
    dimensions (other dimensions remain unchanged).
    @param stride_shape Stride dimensions.
    @param pad_shape Pad dimensions.
    """
    assert len(matrix_shape) >= len(stride_shape)

    stride_shape, pad_shape = np.broadcast_arrays(stride_shape, pad_shape)
    nd = len(stride_shape)
    skirt_size = np.multiply(pad_shape, 2)
    dilate_size = np.subtract(matrix_shape[-nd:], 1) * stride_shape + 1
    return (*matrix_shape[:-nd], *(skirt_size + dilate_size))

def pool_shape(matrix_shape, kernel_shape, stride_shape) -> np_type.NDArray:
    """
    Given the shapes, computes the resulting shape after pooling. Will compute with the pool's dimensions
    (other dimensions remain unchanged).
    @param kernel_shape Pool dimensions.
    @param stride_shape Stride dimensions.
    """
    return correlate_shape(matrix_shape, kernel_shape, stride_shape)

def sliding_window_view(matrix: np_type.NDArray, window_shape, stride_shape=(1,), is_writeable=False) -> np_type.NDArray:
    """
    @param is_writeable Whether the returned view is writeable or not. For safety, the view is read-only by default. See
    `numpy.lib.stride_tricks.as_strided()` for more details. Basically, you at least need to ensure that the
    write-to locations are not overlapping in vectorized operations.
    """
    correlated_shape = correlate_shape(matrix.shape, window_shape, stride_shape)
    nd = len(window_shape)
    stride_shape = np.broadcast_to(stride_shape, nd)
    
    view_shape = (
        *correlated_shape[:-nd],
        *correlated_shape[-nd:],
        *window_shape)
    view_stride = (
        *matrix.strides[:-nd],
        *[stride_shape[di] * matrix.strides[di] for di in range(-nd, 0)],
        *matrix.strides[-nd:])
    return np.lib.stride_tricks.as_strided(matrix, view_shape, view_stride, writeable=is_writeable)

def dilate(matrix: np_type.NDArray, stride_shape, pad_shape=(0,)) -> np_type.NDArray:
    """
    Dilate the matrix according to the specified shapes. Will compute with the stride's and pad's dimensions
    (broadcast the rest).
    @param stride_shape Stride dimensions.
    @param pad_shape Pad dimensions.
    """
    dilated_shape = dilate_shape(matrix.shape, stride_shape, pad_shape)
    
    # Create slice into the dilated matrix so we can assign the "exploded" `matrix` without looping
    step, pad = np.broadcast_arrays(stride_shape, pad_shape)
    nd = len(step)
    size = np.array(dilated_shape[-nd:])
    slices = tuple(slice(pd, sz - pd, st) for pd, sz, st in zip(pad, size, step))

    dilated_matrix = np.zeros(dilated_shape, dtype=matrix.dtype)
    dilated_matrix[..., *slices] = matrix
    return dilated_matrix
    
def correlate(matrix: np_type.NDArray, kernel: np_type.NDArray, stride_shape=(1,), num_kernel_dims=None) -> np_type.NDArray:
    """
    Correlate the matrix according to the specified shapes. Will compute with the kernel's dimensions
    (broadcast the rest). The correlation is performed on regions where the matrix and kernel overlaps
    completely (in a sense similar to `numpy.convolve()`'s `valid` mode).
    @param kernel The kernel to correlate with.
    @param stride_shape Stride dimensions.
    @param num_kernel_dims Number of kernel dimensions. If `None`, will infer from kernel shape. If a value is
    specified, the correlation will be done on the specified dimensions and broadcast to the rest.
    """
    nd = len(kernel.shape) if num_kernel_dims is None else num_kernel_dims
    assert nd <= len(kernel.shape)

    # A view of the matrix with matching kernel dimensions, so correlation is just an element-wise dot
    strided_view = sliding_window_view(matrix, kernel.shape[-nd:], stride_shape)

    # Since kernel dimensions may be specified explicitly, a reshaped view to kernel is needed (e.g., for 
    # vectorized operation on a batch of kernels)
    kernel_view = kernel.reshape((*kernel.shape[:-nd], *([1] * nd), *kernel.shape[-nd:]))

    correlated = np.einsum(_kernel_dim_to_einsum_correlation_expr[nd], strided_view, kernel_view)

    assert np.array_equal(correlated.shape, strided_view.shape[:-nd]), f"shapes: {correlated.shape}, {strided_view.shape}"
    return correlated

def pool(matrix: np_type.NDArray, kernel_shape, stride_shape, mode: com.EPooling) -> np_type.NDArray:
    """
    Perform pooling operation on the matrix according to the specified shapes. Will compute with the pool's dimensions
    (broadcast the rest).
    @param kernel_shape Pool dimensions.
    @param stride_shape Stride dimensions.
    """
    nd = len(kernel_shape)
    strided_view = sliding_window_view(matrix, kernel_shape, stride_shape)
    match mode:
        case com.EPooling.MAX:
            pooled = strided_view.max(axis=tuple(di for di in range(-nd, 0)))
        case com.EPooling.AVERAGE:
            pooled = strided_view.mean(axis=tuple(di for di in range(-nd, 0)))
        case _:
            raise ValueError("unknown pooling mode specified")

    assert np.array_equal(pooled.shape, strided_view.shape[:-nd]), f"shapes: {pooled.shape}, {strided_view.shape[:-nd]}"
    return pooled
