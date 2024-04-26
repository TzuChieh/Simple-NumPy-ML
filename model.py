"""
@brief Contains components for building a neural network.
All 1-D vectors  of `n` elements are assumed to have shape = `(n, 1)` (a column vector).
"""


import vector as vec

import numpy as np
import numpy.typing as np_type

import random
import warnings
import sys
from abc import ABC, abstractmethod
from typing import Iterable
from timeit import default_timer as timer
from datetime import timedelta
    

# Type of the numbers used for calculation. Note that `real_type` can be used for both contructing scalars or for
# specifying `dtype` arguments. `real_dtype` should be used for comparing `dtype`s
real_type = np.float32
real_dtype = np.dtype(real_type)


# An approximative value of machine epsilon, which is useful in avoiding some numerical issues such as division
# by zero. Keras also uses this value, see https://github.com/tensorflow/tensorflow/blob/066e226b3ed6db054cdb5ed0ff2453b8c1ffb3f6/tensorflow/python/keras/backend_config.py#L24
epsilon = real_type(1e-7)


class ActivationFunction(ABC):
    @abstractmethod
    def eval(self, z):
        """
        @param The input vector.
        @return Vector of the evaluated function.
        """
        pass
        
    @abstractmethod
    def jacobian(self, z, **kwargs):
        """
        @param z The input vector.
        @param kwargs Implementation defined extra arguments (e.g., to facilitate the calculation).
        @return A matrix of all the function's first-order derivatives with respect to `z`. For example,
        the 1st row would be (da(z1)/dz1, da(z1)/dz2, ..., da(z1)/dzn),
        the 2nd row would be (da(z2)/dz1, da(z2)/dz2, ..., da(z2)/dzn),
        and so on (all the way to da(zn)/dzn).
        """
        pass


class Layer(ABC):
    """
    Abstraction for a single layer in a neural network. Parameters should be of the defined shape (e.g., a vector)
    in the lowest dimensions, and be broadcastable to higher dimensions.
    """
    def __init__(self):
        super().__init__()

    @property
    @abstractmethod
    def bias(self) -> np_type.NDArray:
        """
        @return The bias parameters.
        """
        pass

    @property
    @abstractmethod
    def weight(self) -> np_type.NDArray:
        """
        @return The weight parameters.
        """
        pass

    @property
    @abstractmethod
    def activation(self) -> ActivationFunction:
        """
        @return The activation function.
        """
        pass

    @property
    @abstractmethod
    def input_shape(self) -> np_type.NDArray:
        """
        @return The dimensions of input in (..., number of channels, height, width).
        """
        pass

    @property
    @abstractmethod
    def output_shape(self) -> np_type.NDArray:
        """
        @return The dimensions of output in (..., number of channels, height, width).
        """
        pass

    @abstractmethod
    def weighted_input(self, x: np_type.NDArray):
        """
        @param x The input activation vector.
        @return The weighted input vector (z).
        """
        pass

    @abstractmethod
    def update_params(self, bias: np_type.NDArray, weight: np_type.NDArray):
        """
        @param bias The new bias parameters.
        @param weight The new weight parameters.
        """
        pass

    @abstractmethod
    def derived_params(self, x: np_type.NDArray, delta: np_type.NDArray):
        """
        @param x The input activation vector.
        @param delta The error vector (dCdz).
        @return Gradient of `bias` and `weight` in the form `(del_b, del_w)`.
        """
        pass

    @abstractmethod
    def feedforward(self, x: np_type.NDArray, **kwargs):
        """
        @param x The input activation vector.
        @param kwargs Implementation defined extra arguments (e.g., to facilitate the calculation).
        @return Activation vector of the layer.
        """
        pass

    @abstractmethod
    def backpropagate(self, delta: np_type.NDArray):
        """
        @param delta The error vector (dCdz).
        @return The error vector (dCdx).
        """
        pass

    @property
    def input_vector_shape(self) -> np_type.NDArray:
        """
        @return A compatible `input_shape` in the form of vector.
        """
        return (*self.input_shape[:-2], self.input_shape[-2:].prod(), 1)

    @property
    def output_vector_shape(self) -> np_type.NDArray:
        """
        @return A compatible `output_shape` in the form of vector.
        """
        return (*self.output_shape[:-2], self.output_shape[-2:].prod(), 1)

    def init_normal_params(self):
        """
        Randomly set initial parameters. The random values forms a standard normal distribution.
        """
        rng = np.random.default_rng()
        b = rng.standard_normal(self.bias.shape, dtype=real_type)
        w = rng.standard_normal(self.weight.shape, dtype=real_type)
        self.update_params(b, w)

    def init_scaled_normal_params(self):
        """
        Scaled (weights) version of `init_normal_params()`. In theory works better for sigmoid and tanh neurons.
        """
        rng = np.random.default_rng()
        nx = self.input_vector_shape[-2]
        b = rng.standard_normal(self.bias.shape, dtype=real_type)
        w = rng.standard_normal(self.weight.shape, dtype=real_type) / np.sqrt(nx, dtype=real_type)
        self.update_params(b, w)


class CostFunction(ABC):
    @abstractmethod
    def eval(self, a, y):
        """
        @return A vector of cost values.
        """
        pass

    @abstractmethod
    def derived_eval(self, a, y):
        """
        This method would have return a jacobian like `ActivationFunction.jacobian()`. However, currently all
        implementations are element-wise independent so we stick with returning a vector.
        @return A vector of derived cost values.
        """
        pass


class Sigmoid(ActivationFunction):
    def eval(self, z):
        a = 1 / (1 + np.exp(-z))
        return a
    
    def jacobian(self, z, **kwargs):
        # Sigmoid is element-wise independent, so its jacobian is simply a diagonal matrix
        a = kwargs['a'] if 'a' in kwargs else self.eval(z)
        dadz = a * (1 - a)
        return np.diagflat(dadz)
    

class Softmax(ActivationFunction):
    def eval(self, z):
        # Improves numerical stability (does not change the result--will cancel out in the division)
        z = z - np.max(z, axis=-2, keepdims=True)
        e_z = np.exp(z)
        a = e_z / np.sum(e_z, axis=-2, keepdims=True)
        return a
    
    def jacobian(self, z, **kwargs):
        # For a derivation that is clean and avoids looping & branching, see
        # https://mattpetersen.github.io/softmax-with-cross-entropy
        a = kwargs['a'] if 'a' in kwargs else self.eval(z)
        dadz = np.diagflat(a) - np.outer(a, a)
        return dadz


class Tanh(ActivationFunction):
    def eval(self, z):
        return np.tanh(z)

    def jacobian(self, z, **kwargs):
        a = kwargs['a'] if 'a' in kwargs else self.eval(z)
        dadz = 1 - np.square(a)
        return np.diagflat(dadz)


class ReLU(ActivationFunction):
    def eval(self, z):
        return z * (z > 0)
    
    def jacobian(self, z, **kwargs):
        # Derivatives at 0 is implemented as 0. See "Numerical influence of ReLU'(0) on backpropagation",
        # https://hal.science/hal-03265059/file/Impact_of_ReLU_prime.pdf
        dadz = (z > 0).astype(real_type)
        return np.diagflat(dadz) 


class Quadratic(CostFunction):
    def eval(self, a, y):
        """
        Basically computing the MSE between activations `a` and desired output `y`. The 0.5 multiplier is
        to make its derived form cleaner (for convenience).
        """
        C = real_type(0.5) * np.linalg.norm(a - y) ** 2
        return C
    
    def derived_eval(self, a, y):
        dCda = a - y
        return dCda
    

class CrossEntropy(CostFunction):
    def eval(self, a, y):
        a = self._adapt_a(a)
        C = np.sum(-y * np.log(a) - (1 - y) * np.log(1 - a))
        return C

    def derived_eval(self, a, y):
        a = self._adapt_a(a)
        dCda = (a - y) / (a * (1 - a))
        return dCda
    
    def _adapt_a(self, a):
        """
        Slightly modify `a` to prevent division by 0 and NaN/Inf in various cost function operations (e.g.,
        the `(1 - y) * log(1 - a)` term can be NaN/Inf).
        """
        # We modify `a` similar to Keras: https://github.com/tensorflow/tensorflow/blob/066e226b3ed6db054cdb5ed0ff2453b8c1ffb3f6/tensorflow/python/keras/backend.py#L5046.
        # `np.nan_to_num()` could be an alternative solution, but it is more intrusive and needs to be tailored
        # for each method.
        return np.clip(a, epsilon, 1 - epsilon)


class FullyConnected(Layer):
    def __init__(
        self, 
        input_shape: Iterable[int],
        output_shape: Iterable[int], 
        activation: ActivationFunction=Sigmoid()):
        """
        @param input_shape Input dimensions, in (..., height, width).
        @param output_shape Output dimensions, in (..., height, width).
        """
        super().__init__()
        self._input_shape = np.array(input_shape)
        self._output_shape = np.array(output_shape)
        self._activation = activation

        ny = self.output_vector_shape[-2]
        nx = self.input_vector_shape[-2]
        self._bias = np.zeros((ny, 1), dtype=real_type)
        self._weight = np.zeros((ny, nx), dtype=real_type)

        self.init_scaled_normal_params()

    @property
    def bias(self):
        return self._bias
    
    @property
    def weight(self):
        return self._weight
    
    @property
    def activation(self):
        return self._activation
    
    @property
    def input_shape(self):
        return self._input_shape

    @property
    def output_shape(self):
        return self._output_shape

    def weighted_input(self, x):
        b = self._bias
        w = self._weight
        z = w @ x + b
        return z
    
    def update_params(self, bias, weight):
        assert self._bias.dtype == real_dtype, f"{self._bias.dtype}"
        assert self._weight.dtype == real_dtype, f"{self._weight.dtype}"

        self._bias = bias
        self._weight = weight

    def derived_params(self, x, delta):
        del_b = np.copy(delta)
        x_T = vec.transpose_2d(x)
        del_w = delta @ x_T
        return (del_b, del_w)

    def feedforward(self, x, **kwargs):
        """
        @param kwargs 'z': `weighted_input` of this layer (`x` will be ignored).
        """
        z = kwargs['z'] if 'z' in kwargs else self.weighted_input(x)
        return self.activation.eval(z)

    def backpropagate(self, delta):
        assert delta.dtype == real_dtype, f"{delta.dtype}"

        dCda = self._weight.T @ delta
        return dCda


class Convolution(Layer):
    """
    Note that the definition of convolution is correlating a kernel in reversed order, but in the field of ML
    I noticed that almost all the sources that I could find uses correlation instead. So here follows the same
    convention, namely, using correlation in the forward pass.
    """
    def __init__(
        self, 
        input_shape: Iterable[int],
        kernel_shape: Iterable[int], 
        stride_shape: Iterable[int], 
        activation: ActivationFunction=Sigmoid()):
        """
        @param kernel_shape Kernel dimensions, in (number of features, height, width).
        @param stride_shape Stride dimensions in 2-D.
        """
        super().__init__()
        
        output_shape = vec.correlate_shape(input_shape, kernel_shape, stride_shape)
        output_shape[-3] *= kernel_shape[0]

        self._input_shape = np.array(input_shape)
        self._output_shape = np.array(output_shape)
        self._kernel_shape = np.array(kernel_shape)
        self._stride_shape = np.array(stride_shape)
        self._activation = activation
        self._bias = np.zeros((kernel_shape[0], 1, 1), dtype=real_dtype)
        self._weight = np.zeros(kernel_shape, dtype=real_type)

        self.init_scaled_normal_params()

    @property
    def bias(self):
        return self._bias
    
    @property
    def weight(self):
        return self._weight
    
    @property
    def activation(self):
        return self._activation
    
    @property
    def input_shape(self):
        return self._input_shape

    @property
    def output_shape(self):
        return self._output_shape
    
    def weighted_input(self, x):
        x = x.reshape(self.input_shape)
        b = self._bias
        k = self._weight

        z = vec.correlate(x, k, self._stride_shape)
        z += b

        assert np.array_equal(z.shape, self.output_shape), f"shapes: {z.shape}, {self.output_shape}"
        return z.reshape(self.output_vector_shape)
    
    def update_params(self, bias, weight):
        self._bias = bias.reshape(self._bias.shape)
        self._weight = weight.reshape(self._weight.shape)

    def derived_params(self, x, delta):
        x = x.reshape(self.input_shape)
        delta = delta.reshape(self.output_shape)

        del_b = delta.sum(axis=(-2, -1), keepdims=True, dtype=real_type)

        # Backpropagation is equivalent to a stride-1 correlation of input with a dilated gradient
        dilated_delta = vec.dilate(delta, self._stride_shape)
        del_w = vec.correlate(x, dilated_delta, stride_shape=(1, 1))

        assert np.array_equal(del_w.shape, self._weight.shape), f"shapes: {del_w.shape}, {self._weight.shape}"
        return (del_b, del_w)

    def feedforward(self, x, **kwargs):
        """
        @param kwargs 'z': `weighted_input` of this layer (`x` will be ignored).
        """
        z = kwargs['z'] if 'z' in kwargs else self.weighted_input(x)
        return self.activation.eval(z)

    def backpropagate(self, delta):
        assert delta.dtype == real_dtype, f"{delta.dtype}"

        delta = delta.reshape(self.output_shape)

        # Backpropagation is equivalent to a stride-1 full correlation of a dilated (and padded) gradient with
        # a reversed kernel
        k = np.flip(self._weight)
        pad_shape = np.subtract(k.shape[-2:], 1)
        dilated_delta = dilate(delta, self._stride_shape, pad_shape=pad_shape)
        dCda = correlate(dilated_delta, k, stride_shape=(1, 1))

        assert np.array_equal(dCda.shape, self.input_shape), f"shapes: {dCda.shape}, {self.input_shape}"
        return dCda.reshape(self.input_vector_shape)


class Network:
    def __init__(self, hidden_layers: Iterable[Layer], cost: CostFunction=CrossEntropy()):
        self.hidden_layers = hidden_layers
        self.num_layers = len(hidden_layers) + 1
        self.cost = cost
        self.init_velocities()

    def feedforward(self, x):
        """
        @param x The input vector.
        """
        a = x
        for layer in self.hidden_layers:
            a = layer.feedforward(a)
        return a
    
    def stochastic_gradient_descent(
        self,
        training_data, 
        num_epochs,
        mini_batch_size,
        gradient_clip_norm=sys.float_info.max,
        momentum=0.0,
        eta=1,
        lambba=0.0,
        test_data=None,
        report_training_performance=False,
        report_test_performance=False,
        report_training_cost=False,
        report_test_cost=False):
        """
        @param gradient_clip_norm Clip threshold for backpropagation gradient based on norm.
        @param eta Learning rate.
        @param lambba The regularization parameter.
        """
        gradient_clip_norm = real_type(np.minimum(gradient_clip_norm, np.finfo(real_type).max))
        momentum = real_type(momentum)
        eta = real_type(eta)
        lambba = real_type(lambba)

        print(f"optimizer: stochastic gradient descent")
        print(f"mini batch size: {mini_batch_size}, gradient clip: {gradient_clip_norm}, momentum: {momentum}")
        print(f"learning rate: {eta}, L2 regularization: {lambba}")

        sgd_start_time = timer()

        for ei in range(num_epochs):
            epoch_start_time = timer()

            random.shuffle(training_data)
            mini_batches = [
                training_data[bi : bi + mini_batch_size]
                for bi in range(0, len(training_data), mini_batch_size)]
            for mini_batch_data in mini_batches:
                self._update_mini_batch(mini_batch_data, eta, gradient_clip_norm, momentum, lambba, len(training_data))
            
            # Collects a brief report for this epoch
            report = ""

            if report_training_performance:
                num, frac = self.performance(training_data)
                report += f"; training perf: {num} / {len(training_data)} ({frac})"

            if report_test_performance:
                assert test_data is not None
                num, frac = self.performance(test_data)
                report += f"; test perf: {num} / {len(test_data)} ({frac})"

            if report_training_cost:
                report += f"; training cost: {self.total_cost(training_data, lambba)}"

            if report_test_cost:
                assert test_data is not None
                report += f"; test cost: {self.total_cost(test_data, lambba)}"

            report += f"; Δt: {timedelta(seconds=(timer() - epoch_start_time))}"

            print(f"epoch {ei + 1} / {num_epochs}{report}")

        print(f"total Δt: {timedelta(seconds=(timer() - sgd_start_time))}")

    def performance(self, dataset):
        """
        @param dataset A list of pairs. Each pair contains input activation (x) and output activation (y).
        @return A tuple that contains (in order): number of correct outputs, fraction of correct outputs.
        """
        results = [(np.argmax(self.feedforward(x)), np.argmax(y)) for x, y in dataset]
        num_right_answers = sum(1 for network_y, y in results if network_y == y)
        num_data = len(dataset)
        return (num_right_answers, num_right_answers / num_data)
    
    def total_cost(self, dataset, lambba):
        """
        @param dataset A list of pairs. Each pair contains input activation (x) and output activation (y).
        @param lambba The regularization parameter.
        @return Total cost of the dataset.
        """
        cost = 0.0
        rcp_dataset_n = 1.0 / len(dataset)
        for x, y in dataset:
            a = self.feedforward(x)
            cost += self.cost.eval(a, y) * rcp_dataset_n

        # L2 regularization term
        sum_w2 = sum(np.linalg.norm(w) ** 2 for w in self.weights)
        cost += lambba * rcp_dataset_n * 0.5 * sum_w2

        return cost

    def init_velocities(self):
        """
        Initialize gradient records.
        """
        self.v_biases = [np.zeros(b.shape, dtype=real_type) for b in self.biases]
        self.v_weights = [np.zeros(w.shape, dtype=real_type) for w in self.weights]

    @property
    def biases(self):
        """
        @return List of biases of the hidden layers.
        """
        return [layer.bias for layer in self.hidden_layers]
    
    @property
    def weights(self):
        """
        @return List of weights of the hidden layers.
        """
        return [layer.weight for layer in self.hidden_layers]

    def _update_mini_batch(self, mini_batch_data, eta, gradient_clip_norm, momentum, lambba, n):
        """
        @param n Number of training samples. To see why dividing by `n` is used for regularization,
        see https://datascience.stackexchange.com/questions/57271/why-do-we-divide-the-regularization-term-by-the-number-of-examples-in-regularize.
        """
        rcp_n = real_type(1.0 / n)
        rcp_mini_batch_n = real_type(1.0 / len(mini_batch_data))

        # Approximating the true `del_b` and `del_w` from m samples for each hidden layer
        del_bs = [np.zeros(layer.bias.shape, dtype=real_type) for layer in self.hidden_layers]
        del_ws = [np.zeros(layer.weight.shape, dtype=real_type) for layer in self.hidden_layers]
        for x, y in mini_batch_data:
            delta_del_bs, delta_del_ws = self._backpropagation(x, y, gradient_clip_norm)
            del_bs = [bi + dbi for bi, dbi in zip(del_bs, delta_del_bs)]
            del_ws = [wi + dwi for wi, dwi in zip(del_ws, delta_del_ws)]
        del_bs = [bi * rcp_mini_batch_n for bi in del_bs]
        del_ws = [wi * rcp_mini_batch_n for wi in del_ws]

        # Update momentum parameters
        self.v_biases = [
            vb * momentum - eta * bi for vb, bi in zip(self.v_biases, del_bs)]
        self.v_weights = [
            vw * momentum - eta * lambba * rcp_n * w - eta * wi for w, vw, wi in zip(self.weights, self.v_weights, del_ws)]

        # Compute new biases and weights
        new_biases = [b + vb for b, vb in zip(self.biases, self.v_biases)]
        new_weights = [w + vw for w, vw in zip(self.weights, self.v_weights)]

        # Update biases and weights
        for layer, new_b, new_w in zip(self.hidden_layers, new_biases, new_weights):
            layer.update_params(new_b, new_w)

    def _backpropagation(self, x, y, gradient_clip_norm):
        """
        @param x Training inputs.
        @param y Training outputs.
        """
        del_bs = [np.zeros(b.shape, dtype=real_type) for b in self.biases]
        del_ws = [np.zeros(w.shape, dtype=real_type) for w in self.weights]
        
        # Forward pass: store activations & weighted inputs (`zs`) layer by layer
        activations = [x]
        zs = []
        for layer in self.hidden_layers:
            z = layer.weighted_input(activations[-1])
            zs.append(z)
            activations.append(layer.feedforward(activations[-1], z=z))

        # Backward pass (initial delta term, must take cost function into account)
        dCda = self.cost.derived_eval(activations[-1], y)
        dadz = self.hidden_layers[-1].activation.jacobian(zs[-1], a=activations[-1])
        delta = dadz.T @ dCda
        delta = self._gradient_clip(delta, gradient_clip_norm)

        # Backward pass (hidden layers)
        del_bs[-1], del_ws[-1] = self.hidden_layers[-1].derived_params(activations[-2], delta)
        for layer_idx in reversed(range(0, self.num_layers - 2)):
            layer = self.hidden_layers[layer_idx]
            next_layer = self.hidden_layers[layer_idx + 1]
            delta = next_layer.backpropagate(delta)
            dadz = layer.activation.jacobian(zs[layer_idx])
            delta = dadz.T @ delta
            delta = self._gradient_clip(delta, gradient_clip_norm)
            del_bs[layer_idx], del_ws[layer_idx] = layer.derived_params(activations[layer_idx], delta)

        return (del_bs, del_ws)

    def _gradient_clip(self, delta, gradient_clip_norm):
        # Potentially apply gradient clipping
        if gradient_clip_norm < np.finfo(real_type).max:
            delta_norm = np.linalg.norm(delta)
            if delta_norm >= gradient_clip_norm:
                delta = delta / delta_norm * gradient_clip_norm
                print(f"clipped {delta}")
        return delta
