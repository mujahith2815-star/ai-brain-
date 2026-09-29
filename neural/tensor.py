"""
Lightweight Tensor Operations & Neural Primitives for P.H.A.S.S Sphere.
Implements vector/matrix math, activations, and dense layers with zero external C++ dependencies.
"""

from __future__ import annotations
import math
import random
from typing import Callable, List, Optional, Tuple


class Tensor:
    """1D/2D Tensor representation for fast local neural inference."""

    def __init__(self, data: List[float] | List[List[float]]):
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            self.data: List[List[float]] = data  # type: ignore
            self.shape: Tuple[int, ...] = (len(data), len(data[0]))
            self.is_2d = True
        else:
            self.data_1d: List[float] = [float(x) for x in data]  # type: ignore
            self.shape = (len(self.data_1d),)
            self.is_2d = False

    @classmethod
    def zeros(cls, *shape: int) -> Tensor:
        if len(shape) == 1:
            return cls([0.0] * shape[0])
        elif len(shape) == 2:
            return cls([[0.0] * shape[1] for _ in range(shape[0])])
        raise ValueError("Only 1D and 2D tensors are supported.")

    @classmethod
    def random_uniform(cls, rows: int, cols: int, low: float = -0.1, high: float = 0.1) -> Tensor:
        return cls([[random.uniform(low, high) for _ in range(cols)] for _ in range(rows)])

    def to_list(self) -> List[float] | List[List[float]]:
        return self.data if self.is_2d else self.data_1d

    def dot(self, vec: List[float]) -> List[float]:
        """Matrix-vector multiplication: Self (M x N) @ vec (N) -> (M)."""
        if not self.is_2d:
            raise ValueError("Dot operation requires 2D weight matrix.")
        rows, cols = self.shape
        if len(vec) != cols:
            raise ValueError(f"Shape mismatch: {self.shape} vs vector length {len(vec)}")

        result = [0.0] * rows
        for i in range(rows):
            s = 0.0
            row_data = self.data[i]
            for j in range(cols):
                s += row_data[j] * vec[j]
            result[i] = s
        return result


# --- Activation Functions ---

def relu(vec: List[float]) -> List[float]:
    return [max(0.0, x) for x in vec]


def sigmoid(vec: List[float]) -> List[float]:
    return [1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, x)))) for x in vec]


def tanh_act(vec: List[float]) -> List[float]:
    return [math.tanh(max(-10.0, min(10.0, x))) for x in vec]


def softmax(vec: List[float]) -> List[float]:
    if not vec:
        return []
    max_val = max(vec)
    exp_vals = [math.exp(max(-20.0, min(20.0, x - max_val))) for x in vec]
    total = sum(exp_vals)
    if total <= 1e-9:
        return [1.0 / len(vec)] * len(vec)
    return [v / total for v in exp_vals]


class DenseLayer:
    def __init__(self, in_features: int, out_features: int, activation: Optional[Callable[[List[float]], List[float]]] = None):
        self.in_features = in_features
        self.out_features = out_features
        # He/Xavier weight initialization
        scale = math.sqrt(2.0 / in_features)
        self.weights = Tensor.random_uniform(out_features, in_features, -scale, scale)
        self.bias = [0.0] * out_features
        self.activation = activation or relu

    def forward(self, x: List[float]) -> List[float]:
        # Linear transform: W @ x + b
        raw = self.weights.dot(x)
        linear = [r + b for r, b in zip(raw, self.bias)]
        return self.activation(linear)
