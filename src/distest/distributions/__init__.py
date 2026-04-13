"""Distribution estimation module: MLE-based parameter estimation.

This module provides classes for estimating probability distribution parameters
using maximum likelihood estimation (MLE), supporting both unbinned (raw) and
binned (histogram) data.

Submodules:
    unbinned_mle: MLE estimation for raw data.
    binned_mle: MLE estimation for histogram data.
    scipy_ext: Scipy integration utilities.
    custom: Templates for custom distribution definitions.
"""

from __future__ import annotations

from .binned_mle import BinnedMLEEstimator
from .custom import (
    CustomBinnedEstimator,
    CustomRVContinuous,
    CustomUnbinnedEstimator,
)
from .unbinned_mle import UnbinnedMLEEstimator

__all__ = [
    # Unbinned MLE
    "UnbinnedMLEEstimator",
    # Binned MLE
    "BinnedMLEEstimator",
    # Custom distributions
    "CustomRVContinuous",
    "CustomUnbinnedEstimator",
    "CustomBinnedEstimator",
]
