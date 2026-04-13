"""Robust statistics for unbinned (raw) data.

Provides robust location, scale, and weight computation for raw observations.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ..core import UnbinnedData
from .functions import (
    estimate_location_and_scale,
    huber_weights,
    tukey_biweight,
)


class RobustLocationScale:
    """Robust estimator for location (median) and scale (MAD).

    Simple standalone estimator without inheritance from BaseEstimator.
    Provides median-based location and MAD-based scale.
    """

    def __init__(
        self,
        location_method: str = "median",
        scale_method: str = "mad",
    ) -> None:
        """Initialize robust estimator.

        Args:
            location_method: Method for location ('median').
            scale_method: Method for scale ('mad' or 'quantile').
        """
        self.location_method = location_method
        self.scale_method = scale_method
        self.location_: float | None = None
        self.scale_: float | None = None

    def fit(self, data: UnbinnedData) -> RobustLocationScale:
        """Fit robust location and scale.

        Args:
            data: UnbinnedData instance.

        Returns:
            self: Fitted estimator.
        """
        self.location_, self.scale_ = estimate_location_and_scale(
            data.values,
            weights=data.weights,
            location_method=self.location_method,
            scale_method=self.scale_method,
        )
        return self

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


class RobustStandardization:
    """Standardize data using robust location and scale.

    Useful for outlier detection and robust z-scores.
    """

    def __init__(
        self,
        location_method: str = "median",
        scale_method: str = "mad",
    ) -> None:
        """Initialize standardizer.

        Args:
            location_method: Location estimation method.
            scale_method: Scale estimation method.
        """
        self.estimator = RobustLocationScale(
            location_method=location_method,
            scale_method=scale_method,
        )

    def fit(self, data: UnbinnedData) -> RobustStandardization:
        """Fit robust statistics.

        Args:
            data: UnbinnedData instance.

        Returns:
            self.
        """
        self.estimator.fit(data)
        return self

    def transform(self, data: UnbinnedData) -> NDArray:
        """Apply robust standardization.

        z = (x - location) / scale

        Args:
            data: UnbinnedData instance.

        Returns:
            Standardized array.
        """
        params = self.estimator.get_params()
        return (data.values - params["location"]) / params["scale"]


class OutlierDetector:
    """Detect outliers using robust methods.

    Computes robust z-scores and identifies outliers beyond threshold.
    """

    def __init__(
        self,
        threshold: float = 2.5,
        location_method: str = "median",
        scale_method: str = "mad",
    ) -> None:
        """Initialize outlier detector.

        Args:
            threshold: Z-score threshold for outlier detection.
            location_method: Location estimation method.
            scale_method: Scale estimation method.
        """
        self.threshold = threshold
        self.standardizer = RobustStandardization(
            location_method=location_method,
            scale_method=scale_method,
        )

    def fit(self, data: UnbinnedData) -> OutlierDetector:
        """Fit robust statistics.

        Args:
            data: UnbinnedData instance.

        Returns:
            self.
        """
        self.standardizer.fit(data)
        return self

    def detect(self, data: UnbinnedData) -> NDArray:
        """Detect outliers.

        Args:
            data: UnbinnedData instance.

        Returns:
            Boolean array indicating outliers (True = outlier).
        """
        z_scores = np.abs(self.standardizer.transform(data))
        return z_scores > self.threshold

    def get_robust_indices(self, data: UnbinnedData) -> NDArray:
        """Get indices of non-outlier (robust) observations.

        Args:
            data: UnbinnedData instance.

        Returns:
            Array of indices for non-outliers.
        """
        outliers = self.detect(data)
        return np.where(~outliers)[0]


class WeightedRobustEstimator:
    """General robust estimator using weighted residuals.

    Computes weights for observations based on residuals (deviations)
    using weight functions like Huber or Tukey biweight.
    Useful for M-estimation framework.
    """

    def __init__(
        self,
        weight_function: str = "tukey",
        tuning: float | None = None,
    ) -> None:
        """Initialize weighted robust estimator.

        Args:
            weight_function: 'huber' or 'tukey' (biweight).
            tuning: Tuning constant. If None, use defaults.
        """
        self.weight_function = weight_function
        if tuning is None:
            self.tuning = 4.685 if weight_function == "tukey" else 1.345
        else:
            self.tuning = tuning

    def compute_weights(self, residuals: NDArray) -> NDArray:
        """Compute weights from residuals.

        Args:
            residuals: Residual array (deviations from model/location).

        Returns:
            Weight array (same shape as residuals).

        Raises:
            ValueError: If weight_function is unknown.
        """
        if self.weight_function == "huber":
            return huber_weights(residuals, tuning=self.tuning)
        elif self.weight_function == "tukey":
            return tukey_biweight(residuals, tuning=self.tuning)
        else:
            raise ValueError(f"Unknown weight_function: {self.weight_function}")

    def fit_with_weights(
        self,
        data: UnbinnedData,
        residuals: NDArray,
    ) -> tuple[float, float, NDArray]:
        """Fit robust statistics and compute weights.

        Computes weights based on residuals, then uses them in fitting.

        Args:
            data: UnbinnedData instance.
            residuals: Residuals (typically from a model).

        Returns:
            Tuple of (location, scale, weights).
        """
        # Compute weights from residuals
        weights_robust = self.compute_weights(residuals)

        # Combine with data weights
        combined_weights = data.weights * weights_robust

        # Fit with combined weights
        location, scale = estimate_location_and_scale(
            data.values,
            weights=combined_weights,
        )

        return location, scale, weights_robust


__all__ = [
    "RobustLocationScale",
    "RobustStandardization",
    "OutlierDetector",
    "WeightedRobustEstimator",
]
