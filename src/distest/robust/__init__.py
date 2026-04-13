"""Robust statistics module: Outlier-resistant statistical estimation.

This module provides robust statistical estimation methods for computing
outlier-resistant location, scale, and weight estimates. Designed for use
on raw data, not as a general curve-fitting engine.

Submodules:
    functions: Utility functions (trimming, winsorizing, weight functions).
    unbinned: Robust statistics for unbinned (raw) data.
    binned: Robust statistics for binned (histogram) data.

Key Principle:
    This module estimates statistics **on data directly**. It does NOT include
    curve-fitting engines. Residual-based fitting is the user's responsibility.
"""

from __future__ import annotations

from .binned import (
    BinnedOutlierDetector,
    RobustHistogramWeights,
    RobustLocationScaleBinned,
)
from .functions import (
    estimate_location_and_scale,
    huber_weights,
    mad,
    mad_scale,
    median,
    quantile_scale,
    trim,
    tukey_biweight,
    winsorize,
)
from .unbinned import (
    OutlierDetector,
    RobustLocationScale,
    RobustStandardization,
    WeightedRobustEstimator,
)

__all__ = [
    # Functions
    "median",
    "mad",
    "trim",
    "winsorize",
    "huber_weights",
    "tukey_biweight",
    "quantile_scale",
    "mad_scale",
    "estimate_location_and_scale",
    # Unbinned classes
    "RobustLocationScale",
    "RobustStandardization",
    "OutlierDetector",
    "WeightedRobustEstimator",
    # Binned classes
    "RobustLocationScaleBinned",
    "BinnedOutlierDetector",
    "RobustHistogramWeights",
]
