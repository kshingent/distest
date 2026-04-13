"""Robust statistical functions for outlier-resistant estimation.

Provides utility functions for trimming, winsorizing, weight computation,
and robust scale/location estimation.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
from numpy.typing import NDArray

# Type alias for weight functions: residuals -> weights
WeightFunction = Callable[[NDArray], NDArray]


def median(values: NDArray, weights: Optional[NDArray] = None) -> float:
    """Compute weighted median.

    Args:
        values: Data array.
        weights: Optional weights (must be positive). If None, uniform.

    Returns:
        Weighted median value.
    """
    values_arr = np.asarray(values, dtype=np.float64).ravel()
    if len(values_arr) == 0:
        raise ValueError("values must not be empty")

    if weights is None:
        return float(np.median(values_arr))

    weights_arr = np.asarray(weights, dtype=np.float64).ravel()
    if len(weights_arr) != len(values_arr):
        raise ValueError("weights length must match values length")

    # Sort by values
    sorted_idx = np.argsort(values_arr)
    sorted_vals = values_arr[sorted_idx]
    sorted_wts = weights_arr[sorted_idx]

    # Cumulative weights
    cumsum_wts = np.cumsum(sorted_wts)
    half_sum = cumsum_wts[-1] / 2.0

    # Find index where cumsum >= half_sum
    idx = np.searchsorted(cumsum_wts, half_sum, side='left')
    idx = min(idx, len(sorted_vals) - 1)
    return float(sorted_vals[idx])


def mad(values: NDArray, weights: Optional[NDArray] = None) -> float:
    """Compute Median Absolute Deviation.

    MAD = median(|values - median(values)|)
    For normal distribution: std ≈ 1.4826 * MAD

    Args:
        values: Data array.
        weights: Optional weights.

    Returns:
        MAD value.
    """
    values_arr = np.asarray(values, dtype=np.float64).ravel()
    med = median(values_arr, weights=weights)
    abs_dev = np.abs(values_arr - med)
    return median(abs_dev, weights=weights)


def trim(
    values: NDArray,
    weights: Optional[NDArray] = None,
    fraction: Optional[float] = None,
    count: Optional[int] = None,
) -> tuple[NDArray, NDArray]:
    """Trim (remove) extreme values.

    Removes the lowest `fraction` and highest `fraction` (or `count` on each side).

    Args:
        values: Data array.
        weights: Optional weights.
        fraction: Fraction to trim from each tail (0 < fraction < 0.5).
                  If provided, count is ignored.
        count: Number of observations to trim from each tail.
               Used only if fraction is None.

    Returns:
        Tuple of (trimmed_values, trimmed_weights).

    Raises:
        ValueError: If neither fraction nor count is specified.
    """
    values_arr = np.asarray(values, dtype=np.float64).ravel()
    n = len(values_arr)

    if fraction is not None:
        if not (0 < fraction < 0.5):
            raise ValueError("fraction must be in (0, 0.5)")
        n_trim = int(np.ceil(n * fraction))
    elif count is not None:
        if not (0 < count < n // 2):
            raise ValueError("count must be in (0, n/2)")
        n_trim = count
    else:
        raise ValueError("Either fraction or count must be specified")

    # Sort indices
    sorted_idx = np.argsort(values_arr)

    # Keep middle part
    keep_idx = sorted_idx[n_trim : n - n_trim]

    trimmed_vals = values_arr[keep_idx]
    if weights is not None:
        weights_arr = np.asarray(weights, dtype=np.float64).ravel()
        trimmed_wts = weights_arr[keep_idx]
    else:
        trimmed_wts = None

    return trimmed_vals, trimmed_wts


def winsorize(
    values: NDArray,
    weights: Optional[NDArray] = None,
    limits: Optional[tuple[float, float]] = None,
    fraction: Optional[float] = None,
) -> NDArray:
    """Winsorize (cap) extreme values.

    Replaces values below `limits[0]` with `limits[0]`, and above `limits[1]`
    with `limits[1]`, or uses quantiles based on `fraction`.

    Args:
        values: Data array.
        weights: Optional weights (ignored; used for compatibility).
        limits: (lower_limit, upper_limit). If None, computed from fraction.
        fraction: Fraction for quantile-based limits. If provided, limits is ignored.

    Returns:
        Winsorized array (same shape as input).

    Raises:
        ValueError: If neither limits nor fraction specified.
    """
    values_arr = np.asarray(values, dtype=np.float64)
    orig_shape = values_arr.shape
    values_arr = values_arr.ravel()

    if fraction is not None:
        if not (0 < fraction < 0.5):
            raise ValueError("fraction must be in (0, 0.5)")
        lower_limit = float(np.quantile(values_arr, fraction))
        upper_limit = float(np.quantile(values_arr, 1.0 - fraction))
    elif limits is not None:
        lower_limit, upper_limit = limits
    else:
        raise ValueError("Either limits or fraction must be specified")

    # Cap values
    capped = np.clip(values_arr, lower_limit, upper_limit)
    return capped.reshape(orig_shape)


def huber_weights(
    residuals: NDArray,
    tuning: float = 1.345,
) -> NDArray:
    """Compute Huber weight function.

    w(r) = 1 if |r| <= tuning, else tuning / |r|
    Smooth transition from quadratic to linear at threshold.

    Args:
        residuals: Residuals or deviations.
        tuning: Tuning constant (threshold).

    Returns:
        Weight array (same shape as residuals).
    """
    residuals_arr = np.asarray(residuals, dtype=np.float64)
    abs_res = np.abs(residuals_arr)
    weights = np.ones_like(residuals_arr)
    mask = abs_res > tuning
    weights[mask] = tuning / abs_res[mask]
    return weights


def tukey_biweight(
    residuals: NDArray,
    tuning: float = 4.685,
) -> NDArray:
    """Compute Tukey biweight (bisquare) weight function.

    w(r) = (1 - (r/tuning)^2)^2 if |r| < tuning, else 0
    Gives zero weight to distant outliers (hard rejection).

    Args:
        residuals: Residuals or deviations.
        tuning: Tuning constant (cutoff).

    Returns:
        Weight array (same shape as residuals).
    """
    residuals_arr = np.asarray(residuals, dtype=np.float64)
    abs_res = np.abs(residuals_arr)
    normalized = abs_res / tuning
    weights = np.zeros_like(residuals_arr)
    mask = normalized < 1.0
    weights[mask] = (1.0 - normalized[mask] ** 2) ** 2
    return weights


def quantile_scale(
    values: NDArray,
    weights: Optional[NDArray] = None,
    q_low: float = 0.25,
    q_high: float = 0.75,
) -> float:
    """Compute robust scale using inter-quantile range.

    scale = (Q_high - Q_low) / (2 * Phi_inv(q_high))
    For standard normal: (Q3 - Q1) / 1.349 (approximately)

    Args:
        values: Data array.
        weights: Optional weights.
        q_low: Lower quantile (default: 0.25 for quartile).
        q_high: Upper quantile (default: 0.75 for quartile).

    Returns:
        Robust scale estimate.
    """
    values_arr = np.asarray(values, dtype=np.float64).ravel()

    # Compute quantiles (weighted if weights provided)
    if weights is None:
        q_l = np.quantile(values_arr, q_low)
        q_h = np.quantile(values_arr, q_high)
    else:
        weights_arr = np.asarray(weights, dtype=np.float64).ravel()
        sorted_idx = np.argsort(values_arr)
        sorted_vals = values_arr[sorted_idx]
        sorted_wts = weights_arr[sorted_idx]
        cumsum_wts = np.cumsum(sorted_wts)
        total = cumsum_wts[-1]

        # Find quantiles
        idx_l = np.searchsorted(cumsum_wts, total * q_low)
        idx_h = np.searchsorted(cumsum_wts, total * q_high)
        q_l = sorted_vals[min(idx_l, len(sorted_vals) - 1)]
        q_h = sorted_vals[min(idx_h, len(sorted_vals) - 1)]

    iqr = q_h - q_l
    # Standardization constant (Phi_inv(q_high) - Phi_inv(q_low)) for default 0.25/0.75
    # is approximately 0.6745 * 2 = 1.349
    from scipy.stats import norm as normal

    z_low = normal.ppf(q_low)
    z_high = normal.ppf(q_high)
    z_diff = z_high - z_low
    scale = iqr / z_diff if z_diff != 0 else 1.0
    return float(max(scale, 1e-10))


def mad_scale(values: NDArray, weights: Optional[NDArray] = None) -> float:
    """Compute robust scale using MAD (Median Absolute Deviation).

    For normal distribution: std ≈ 1.4826 * MAD

    Args:
        values: Data array.
        weights: Optional weights.

    Returns:
        Robust scale estimate (normalized for normal distribution).
    """
    mad_val = mad(values, weights=weights)
    return 1.4826 * mad_val


def estimate_location_and_scale(
    values: NDArray,
    weights: Optional[NDArray] = None,
    location_method: str = "median",
    scale_method: str = "mad",
) -> tuple[float, float]:
    """Estimate location and scale using robust methods.

    Args:
        values: Data array.
        weights: Optional weights.
        location_method: 'median' or others (extended as needed).
        scale_method: 'mad' or 'quantile'.

    Returns:
        Tuple of (location, scale).

    Raises:
        ValueError: If method is unknown.
    """
    if location_method == "median":
        loc = median(values, weights=weights)
    else:
        raise ValueError(f"Unknown location_method: {location_method}")

    if scale_method == "mad":
        scale = mad_scale(values, weights=weights)
    elif scale_method == "quantile":
        scale = quantile_scale(values, weights=weights)
    else:
        raise ValueError(f"Unknown scale_method: {scale_method}")

    return loc, scale


__all__ = [
    "median",
    "mad",
    "trim",
    "winsorize",
    "huber_weights",
    "tukey_biweight",
    "quantile_scale",
    "mad_scale",
    "estimate_location_and_scale",
    "WeightFunction",
]
