"""Robust statistics for binned (histogram) data.

Provides robust location and scale estimation from histogram data.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from numpy.typing import NDArray

from ..core import HistogramData


class RobustLocationScaleBinned:
    """Robust location and scale estimation from histogram data.

    Estimates median (location) and scale using bin-based statistics.
    """

    def __init__(
        self,
        location_method: str = "median",
        scale_method: str = "mad",
    ) -> None:
        """Initialize binned robust estimator.

        Args:
            location_method: Method for location ('median').
            scale_method: Method for scale ('mad' or 'quantile').
        """
        self.location_method = location_method
        self.scale_method = scale_method
        self.location_: float | None = None
        self.scale_: float | None = None

    def fit(self, data: HistogramData) -> RobustLocationScaleBinned:
        """Fit robust location and scale from histogram.

        Args:
            data: HistogramData instance.

        Returns:
            self: Fitted estimator.
        """
        # Estimate location (median) from histogram
        self.location_ = self._estimate_location(data)

        # Estimate scale from histogram
        self.scale_ = self._estimate_scale(data)

        return self

    def _estimate_location(self, data: HistogramData) -> float:
        """Estimate median from histogram using cumulative distribution.

        Uses linear interpolation within the median bin.

        Args:
            data: HistogramData instance.

        Returns:
            Estimated median.
        """
        cumsum_counts = np.cumsum(data.weights * data.counts)
        total_count = cumsum_counts[-1]
        half_count = total_count / 2.0

        # Find bin containing median
        idx = np.searchsorted(cumsum_counts, half_count, side='left')
        idx = min(idx, len(cumsum_counts) - 1)

        if idx == 0:
            # Median is in first bin
            bin_left = data.edges[0]
            bin_right = data.edges[1]
            bin_count = data.weights[0] * data.counts[0]
            cum_before = 0.0
        else:
            # Median is in bin idx
            bin_left = data.edges[idx]
            bin_right = data.edges[idx + 1]
            bin_count = data.weights[idx] * data.counts[idx]
            cum_before = cumsum_counts[idx - 1]

        # Linear interpolation within bin
        frac_in_bin = (half_count - cum_before) / max(bin_count, 1e-10)
        frac_in_bin = np.clip(frac_in_bin, 0.0, 1.0)
        median = bin_left + frac_in_bin * (bin_right - bin_left)

        return float(median)

    def _estimate_scale(self, data: HistogramData) -> float:
        """Estimate scale from histogram.

        Uses MAD-based or quantile-based method on bin centers
        weighted by counts.

        Args:
            data: HistogramData instance.

        Returns:
            Estimated scale.
        """
        location = self.location_
        if location is None:
            location = self._estimate_location(data)

        if self.scale_method == "mad":
            # Compute MAD from histogram bin information
            abs_deviations = np.abs(data.centers - location)
            # Weighted median of absolute deviations
            cumsum_counts = np.cumsum(data.weights * data.counts)
            total = cumsum_counts[-1]
            half_total = total / 2.0
            idx_mad = np.searchsorted(cumsum_counts, half_total, side='left')
            if idx_mad < len(abs_deviations):
                mad_val = abs_deviations[min(idx_mad, len(abs_deviations) - 1)]
            else:
                mad_val = abs_deviations[-1]
            scale = 1.4826 * mad_val

        elif self.scale_method == "quantile":
            # Quantile-based scale
            scale = self._estimate_scale_quantile(data)
        else:
            raise ValueError(f"Unknown scale_method: {self.scale_method}")

        return float(max(scale, 1e-10))

    def _estimate_scale_quantile(self, data: HistogramData) -> float:
        """Estimate scale using inter-quantile range from histogram.

        Args:
            data: HistogramData instance.

        Returns:
            Quantile-based scale estimate.
        """
        from scipy.stats import norm

        # Compute weighted quantiles at 0.25 and 0.75
        cumsum_counts = np.cumsum(data.weights * data.counts)
        total = cumsum_counts[-1]

        q25_target = total * 0.25
        q75_target = total * 0.75

        # Find quantile bins
        idx_25 = np.searchsorted(cumsum_counts, q25_target, side='left')
        idx_75 = np.searchsorted(cumsum_counts, q75_target, side='left')

        idx_25 = min(idx_25, len(data.centers) - 1)
        idx_75 = min(idx_75, len(data.centers) - 1)

        q25 = data.centers[idx_25]
        q75 = data.centers[idx_75]

        iqr = q75 - q25
        z_diff = norm.ppf(0.75) - norm.ppf(0.25)
        scale = iqr / z_diff if z_diff != 0 else 1.0

        return float(scale)

    def get_params(self) -> dict[str, float]:
        """Get fitted parameters.

        Returns:
            Dictionary with 'location' and 'scale'.

        Raises:
            RuntimeError: If called before fit().
        """
        if self.location_ is None or self.scale_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")
        return {
            "location": float(self.location_),
            "scale": float(self.scale_),
        }


class BinnedOutlierDetector:
    """Detect outliers from histogram data using robust methods.

    Identifies bins that are far from robust median in terms of
    robust standard deviations.
    """

    def __init__(
        self,
        threshold: float = 3.0,
        location_method: str = "median",
        scale_method: str = "mad",
    ) -> None:
        """Initialize binned outlier detector.

        Args:
            threshold: Threshold (in robust std) for outlier bins.
            location_method: Location estimation method.
            scale_method: Scale estimation method.
        """
        self.threshold = threshold
        self.estimator = RobustLocationScaleBinned(
            location_method=location_method,
            scale_method=scale_method,
        )

    def fit(self, data: HistogramData) -> BinnedOutlierDetector:
        """Fit robust statistics.

        Args:
            data: HistogramData instance.

        Returns:
            self.
        """
        self.estimator.fit(data)
        return self

    def detect(self, data: HistogramData) -> NDArray:
        """Detect outlier bins.

        Args:
            data: HistogramData instance.

        Returns:
            Boolean array indicating outlier bins.
        """
        params = self.estimator.get_params()
        z_scores = np.abs((data.centers - params["location"]) / params["scale"])
        return z_scores > self.threshold


class RobustHistogramWeights:
    """Compute bin weights for robust histogram analysis.

    Assigns higher weights to bins near center, lower to extremes.
    """

    def __init__(self, method: str = "huber") -> None:
        """Initialize weight computer.

        Args:
            method: Weight function ('huber' or 'tukey').
        """
        self.method = method

    def compute_weights(
        self,
        data: HistogramData,
        location: Optional[float] = None,
        scale: Optional[float] = None,
    ) -> NDArray:
        """Compute robust weights for histogram bins.

        Args:
            data: HistogramData instance.
            location: Center point (if None, use median of centers).
            scale: Scale parameter (if None, use unit).

        Returns:
            Weight array for bins.
        """
        if location is None:
            location = float(np.average(data.centers, weights=data.counts))
        if scale is None:
            scale = 1.0

        # Compute normalized deviations
        std_deviations = (data.centers - location) / max(scale, 1e-10)

        if self.method == "huber":
            # Huber weights: 1 if |x| <= tuning, else tuning/|x|
            tuning = 1.345
            abs_std = np.abs(std_deviations)
            weights = np.ones_like(abs_std)
            mask = abs_std > tuning
            weights[mask] = tuning / abs_std[mask]

        elif self.method == "tukey":
            # Tukey biweight: (1 - (x/tuning)^2)^2 if |x| < tuning, else 0
            tuning = 4.685
            normalized = std_deviations / tuning
            weights = np.zeros_like(normalized)
            mask = np.abs(normalized) < 1.0
            weights[mask] = (1.0 - normalized[mask] ** 2) ** 2

        else:
            raise ValueError(f"Unknown method: {self.method}")

        return weights


__all__ = [
    "RobustLocationScaleBinned",
    "BinnedOutlierDetector",
    "RobustHistogramWeights",
]
