"""distest: Versatile statistical estimation library for unbinned and binned data.

Main package initialization. Exports core data structures and top-level API.
"""

from __future__ import annotations

from .core import (
    BaseEstimator,
    HistogramData,
    UnbinnedData,
    is_numeric_stable,
    validate_histogram_data,
    validate_unbinned_data,
    validate_weights,
)

__version__ = "0.1.0"

__all__ = [
    "HistogramData",
    "UnbinnedData",
    "BaseEstimator",
    "validate_histogram_data",
    "validate_unbinned_data",
    "validate_weights",
    "is_numeric_stable",
]
