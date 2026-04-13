"""Core data structures and base classes for distest.

This module provides fundamental data types for histogram and unbinned data,
base estimator interface, and validation utilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray

# Type aliases for clarity
FloatArray = NDArray[np.floating[Any]]
IntArray = NDArray[np.integer[Any]]


class HistogramData:
    """Container for histogram data (binned observations).

    This class represents histogram data with bin edges, bin centers, and counts.
    Optionally supports per-bin weights for weighted likelihood estimation.

    Attributes:
        edges (NDArray): Bin edges (length: n_bins + 1). Must be strictly increasing.
        centers (NDArray): Bin centers (length: n_bins).
            Automatically computed as (edges[:-1] + edges[1:]) / 2 if not provided.
        counts (NDArray): Observed counts per bin (length: n_bins).
            Must be non-negative integers or floats.
        weights (Optional[NDArray]): Per-bin weights (length: n_bins).
            If None, uniform weights (all 1.0) are assumed.
    """

    def __init__(
        self,
        edges: NDArray,
        counts: NDArray,
        centers: Optional[NDArray] = None,
        weights: Optional[NDArray] = None,
    ) -> None:
        """Initialize HistogramData.

        Args:
            edges: Bin edges (length: n_bins + 1), strictly increasing.
            counts: Observed counts per bin (length: n_bins).
            centers: Bin centers. If None, computed as (edges[:-1] + edges[1:]) / 2.
            weights: Per-bin weights. If None, uniform weights are assumed.

        Raises:
            ValueError: If edges/counts shapes are inconsistent or data is invalid.
        """
        self.edges = np.asarray(edges, dtype=np.float64)
        self.counts = np.asarray(counts, dtype=np.float64)

        # Validate edges
        if self.edges.ndim != 1:
            raise ValueError(f"edges must be 1D, got shape {self.edges.shape}")
        if len(self.edges) < 2:
            raise ValueError(f"edges must have at least 2 elements, got {len(self.edges)}")
        if not np.all(np.diff(self.edges) > 0):
            raise ValueError("edges must be strictly increasing")

        n_bins = len(self.edges) - 1

        # Validate counts
        if self.counts.ndim != 1:
            raise ValueError(f"counts must be 1D, got shape {self.counts.shape}")
        if len(self.counts) != n_bins:
            raise ValueError(
                f"counts length ({len(self.counts)}) must match number of bins ({n_bins})"
            )
        if not np.all(self.counts >= 0):
            raise ValueError("counts must be non-negative")

        # Set centers
        if centers is None:
            self.centers = (self.edges[:-1] + self.edges[1:]) / 2.0
        else:
            self.centers = np.asarray(centers, dtype=np.float64)
            if self.centers.ndim != 1:
                raise ValueError(f"centers must be 1D, got shape {self.centers.shape}")
            if len(self.centers) != n_bins:
                raise ValueError(
                    f"centers length ({len(self.centers)}) must match number of bins ({n_bins})"
                )

        # Set weights
        if weights is None:
            self.weights = np.ones(n_bins, dtype=np.float64)
        else:
            self.weights = np.asarray(weights, dtype=np.float64)
            if self.weights.ndim != 1:
                raise ValueError(f"weights must be 1D, got shape {self.weights.shape}")
            if len(self.weights) != n_bins:
                raise ValueError(
                    f"weights length ({len(self.weights)}) must match number of bins ({n_bins})"
                )
            if not np.all(self.weights > 0):
                raise ValueError("weights must be strictly positive")

    @property
    def n_bins(self) -> int:
        """Number of bins."""
        return len(self.edges) - 1

    @property
    def bin_widths(self) -> NDArray:
        """Width of each bin."""
        return np.diff(self.edges)

    @property
    def total_count(self) -> float:
        """Total count across all bins."""
        return float(np.sum(self.counts))

    def __repr__(self) -> str:
        return (
            f"HistogramData(n_bins={self.n_bins}, "
            f"total_count={self.total_count:.0f}, "
            f"x_range=[{self.edges[0]:.4g}, {self.edges[-1]:.4g}])"
        )


class UnbinnedData:
    """Container for unbinned (raw) data.

    Represents raw observed data points with optional observation weights
    for weighted maximum likelihood estimation.

    Attributes:
        values (NDArray): Observed data points (1D array).
        weights (Optional[NDArray]): Observation weights (1D array).
            If None, uniform weights (all 1.0) are assumed.
            Length must match len(values).
    """

    def __init__(
        self,
        values: NDArray,
        weights: Optional[NDArray] = None,
    ) -> None:
        """Initialize UnbinnedData.

        Args:
            values: Observed data points (1D array).
            weights: Observation weights. If None, uniform weights are assumed.

        Raises:
            ValueError: If values shape is invalid or weights/values mismatch.
        """
        self.values = np.asarray(values, dtype=np.float64)

        # Validate values
        if self.values.ndim != 1:
            raise ValueError(f"values must be 1D, got shape {self.values.shape}")
        if len(self.values) == 0:
            raise ValueError("values must have at least one element")

        # Set weights
        if weights is None:
            self.weights = np.ones(len(self.values), dtype=np.float64)
        else:
            self.weights = np.asarray(weights, dtype=np.float64)
            if self.weights.ndim != 1:
                raise ValueError(f"weights must be 1D, got shape {self.weights.shape}")
            if len(self.weights) != len(self.values):
                raise ValueError(
                    f"weights length ({len(self.weights)}) must match "
                    f"values length ({len(self.values)})"
                )
            if not np.all(self.weights > 0):
                raise ValueError("weights must be strictly positive")

    @property
    def n_obs(self) -> int:
        """Number of observations."""
        return len(self.values)

    @property
    def total_weight(self) -> float:
        """Total sum of weights."""
        return float(np.sum(self.weights))

    @property
    def effective_sample_size(self) -> float:
        """Effective sample size (sum of weights squared / sum of weights)."""
        w = self.weights
        return float((np.sum(w) ** 2) / np.sum(w**2))

    def __repr__(self) -> str:
        return (
            f"UnbinnedData(n_obs={self.n_obs}, "
            f"total_weight={self.total_weight:.4g}, "
            f"x_range=[{np.min(self.values):.4g}, {np.max(self.values):.4g}])"
        )


class BaseEstimator(ABC):
    """Abstract base class for parameter estimators.

    Defines the interface that all estimator classes (MLE, robust statistics)
    must implement. Follows scikit-learn conventions for consistency.
    """

    @abstractmethod
    def fit(self, data: UnbinnedData | HistogramData) -> BaseEstimator:
        """Fit the estimator to data.

        Args:
            data: UnbinnedData or HistogramData to fit.

        Returns:
            self: Returns the fitted estimator instance.

        Raises:
            ValueError: If data is invalid or fitting fails.
        """
        raise NotImplementedError

    @abstractmethod
    def get_params(self) -> dict[str, float]:
        """Get fitted parameters.

        Returns:
            Dictionary mapping parameter names to estimated values.
            Must be callable after fit().

        Raises:
            RuntimeError: If called before fit().
        """
        raise NotImplementedError

    def predict(self, data: UnbinnedData | HistogramData) -> NDArray:
        """Predict (apply) the model to data.

        For distribution estimation, typically returns log-likelihood or
        predicted densities. Implementation depends on subclass.

        Args:
            data: Data to predict on.

        Returns:
            Predictions (semantics depend on subclass).

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError


def validate_histogram_data(data: object) -> HistogramData:
    """Validate and coerce object to HistogramData.

    Args:
        data: Object to validate.

    Returns:
        HistogramData instance.

    Raises:
        TypeError: If data is not HistogramData or dict-like.
        ValueError: If data is invalid.
    """
    if isinstance(data, HistogramData):
        return data
    raise TypeError(f"Expected HistogramData, got {type(data).__name__}")


def validate_unbinned_data(data: object) -> UnbinnedData:
    """Validate and coerce object to UnbinnedData.

    Args:
        data: Object to validate.

    Returns:
        UnbinnedData instance.

    Raises:
        TypeError: If data is not UnbinnedData.
        ValueError: If data is invalid.
    """
    if isinstance(data, UnbinnedData):
        return data
    raise TypeError(f"Expected UnbinnedData, got {type(data).__name__}")


def validate_weights(
    weights: Optional[NDArray], n: int, name: str = "weights"
) -> NDArray:
    """Validate weight array.

    Args:
        weights: Weight array or None.
        n: Expected length.
        name: Parameter name for error messages.

    Returns:
        Float64 ndarray of weights (uniform if input is None).

    Raises:
        ValueError: If weights are invalid.
    """
    if weights is None:
        return np.ones(n, dtype=np.float64)
    weights_arr = np.asarray(weights, dtype=np.float64)
    if weights_arr.shape != (n,):
        raise ValueError(f"{name} shape {weights_arr.shape} != expected ({n},)")
    if not np.all(weights_arr > 0):
        raise ValueError(f"{name} must be strictly positive")
    return weights_arr


def is_numeric_stable(
    values: NDArray, min_val: float = 1e-300, max_val: float = 1e300
) -> bool:
    """Check if values are numerically stable (no inf, nan, or extreme values).

    Args:
        values: Array to check.
        min_val: Minimum allowed absolute value (non-zero values).
        max_val: Maximum allowed absolute value.

    Returns:
        True if all values are stable.
    """
    if not np.all(np.isfinite(values)):
        return False
    nonzero = values[values != 0]
    if len(nonzero) > 0:
        abs_vals = np.abs(nonzero)
        if np.any(abs_vals < min_val) or np.any(abs_vals > max_val):
            return False
    return True


__all__ = [
    "HistogramData",
    "UnbinnedData",
    "BaseEstimator",
    "validate_histogram_data",
    "validate_unbinned_data",
    "validate_weights",
    "is_numeric_stable",
    "FloatArray",
    "IntArray",
]
