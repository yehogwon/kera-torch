import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from abc import *

import numpy as np

from typing import Optional, Union, Any, Tuple, List
from numbers import Number

from common.grad import *
from util import matrix

# FIXME: What if :: A = A + B
# TODO: other functionalities such as indexing, slicing, ...
class GradArray: 
    def __init__(self, array: Optional[np.ndarray]=None, grad: Optional[np.ndarray]=None, grad_op: Optional[Grad]=None) -> None:
        self._array: np.ndarray = array
        self._grad: np.ndarray = grad
        self._grad_op: Grad = grad_op
    
    def backward(self, grad: np.ndarray) -> None:
        self._grad = grad
        if self._grad_op: 
            upstream_grads = self._grad_op(self._grad)
            for i, upstream_grad in enumerate(upstream_grads):
                if self._grad_op.is_leaf(): 
                    break
                prev_input = self._grad_op._inputs[i]
                if isinstance(prev_input, GradArray): 
                    prev_input.backward(upstream_grad)
    
    def reshape(self, *args: Any, **kwargs: Any) -> 'GradArray':
        _array_, _grad_ = self._array.copy(), self._grad.copy()
        new_ = GradArray(_array_.reshape(*args, **kwargs), _grad_.reshape(*args, **kwargs))
        new_._grad_op = ReshapeGrad(self._array)
        return new_
    
    @property
    def shape(self) -> Tuple[int]:
        if self._array is None:
            raise ValueError("either array or grad is not initialized")
        if self._grad is not None and self._array.shape != self._grad.shape:
            raise ValueError(f"shape of array and grad must be same, but got {self._array.shape} and {self._grad.shape}")
        return self._array.shape
    
    @property
    def n_dim(self) -> int: 
        return len(self.shape)
    
    @property
    def T(self) -> 'GradArray':
        grad_T = None if self._grad is None else self._grad.T
        return GradArray(self._array.copy().T, grad_T, grad_op=TransposeGrad(self))

    def __add__(self, rhs: Union[Number, 'GradArray']) -> 'GradArray':
        return GradArray(self._array + rhs._array, grad_op=AddGrad(self, rhs))
    
    def __radd__(self, lhs: Union[Number, 'GradArray']) -> 'GradArray':
        return GradArray(lhs._array + self._array, grad_op=AddGrad(lhs, self))
    
    def __sub__(self, rhs: Union[Number, 'GradArray']) -> 'GradArray':
        return GradArray(self._array - rhs._array, grad_op=AddGrad(self, -rhs))
    
    def __rsub__(self, lhs: Union[Number, 'GradArray']) -> 'GradArray':
        return GradArray(lhs._array - self._array, grad_op=AddGrad(lhs, -self))
    
    # TODO: elementwise multiplication support (backward)
    def __mul__(self, rhs: Union[Number, 'GradArray']) -> 'GradArray':
        if isinstance(rhs, Number):
            rhs = GradArray(rhs)
        else: 
            raise TypeError(f"unsupported type {type(rhs)}")
        return GradArray(self._array * rhs._array, grad_op=ScalarMulGrad(rhs, self))
    
    def __rmul__(self, lhs: Union[Number, 'GradArray']) -> 'GradArray':
        if isinstance(lhs, Number):
            lhs = GradArray(lhs)
        else: 
            raise TypeError(f"unsupported type {type(lhs)}")
        return GradArray(lhs._array * self._array, grad_op=ScalarMulGrad(lhs, self))
    
    # TODO: elementwise division support (backward)
    def __truediv__(self, rhs: Union[Number, 'GradArray']) -> 'GradArray':
        if isinstance(rhs, Number):
            rhs = GradArray(rhs)
        else: 
            raise TypeError(f"unsupported type {type(rhs)}")
        inv_rhs = GradArray(1 / rhs._array)
        return GradArray(self._array / rhs._array, grad_op=ScalarMulGrad(inv_rhs, self))
    
    def __matmul__(self, rhs: 'GradArray') -> 'GradArray':
        return GradArray(self._array @ rhs._array, grad_op=MatMulGrad(self, rhs))
    
    def __rmatmul__(self, lhs: 'GradArray') -> 'GradArray':
        return GradArray(lhs._array @ self._array, grad_op=MatMulGrad(lhs, self))
    
    def __neg__(self) -> 'GradArray':
        minus = GradArray(np.array(-1))
        return GradArray(-self._array.copy(), grad_op=ScalarMulGrad(minus, self))
    
    def __pow__(self, exponent: float) -> 'GradArray':
        return GradArray(np.power(self._array, exponent), grad_op=PowerGrad(self, exponent))

def expand(arr: GradArray, dim: int) -> GradArray: # only supports vector to 2-dim array (matrix)
    if arr.n_dim > 1: 
        raise ValueError("expand only works for 1-dim array (vector)")
    return GradArray(np.tile(arr._array, reps=(dim, 1)), grad_op=ExpandGrad())

def sum(arr: GradArray, axis: int) -> GradArray: 
    return GradArray(np.sum(arr._array, axis=axis), grad_op=SumGrad(arr))

def l2_norm_square(arr: GradArray, axis: int) -> GradArray: 
    return sum(arr ** 2, axis=axis)
