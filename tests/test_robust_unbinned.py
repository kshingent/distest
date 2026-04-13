"""Tests for distest.robust module (unbinned)."""

import pytest
import numpy as np
from distest.robust import (
    median, mad, trim, winsorize, huber_weights, tukey_biweight,
    RobustLocationScale, OutlierDetector, WeightedRobustEstimator,
)


class TestMedian:
    """Tests for median function."""

    def test_median_odd_length(self):
        """Test median with odd number of values."""
        values = np.array([1.0, 3.0, 2.0])
        assert median(values) == 2.0

    def test_median_even_length(self):
        """Test median with even number of values."""
        values = np.array([1.0, 2.0, 3.0, 4.0])
        assert np.isclose(median(values), 2.5)

    def test_median_with_weights(self):
        """Test weighted median."""
        values = np.array([1.0, 2.0, 3.0])
        weights = np.array([1.0, 1.0, 10.0])  # Heavy weight on 3.0
        result = median(values, weights=weights)
        assert result == 3.0

    def test_median_empty_raises(self):
        """Test that empty array raises error."""
        with pytest.raises(ValueError, match="not be empty"):
            median(np.array([]))


class TestMAD:
    """Tests for MAD (Median Absolute Deviation) function."""

    def test_mad_symmetric(self):
        """Test MAD on symmetric data."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mad_val = mad(values)
        # Median = 3, |dev| = [2, 1, 0, 1, 2], median of |dev| = 1
        assert np.isclose(mad_val, 1.0)

    def test_mad_with_outlier(self):
        """Test MAD is relatively unaffected by outlier."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        values_with_outlier = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 100.0])
        mad1 = mad(values)
        mad2 = mad(values_with_outlier)
        # MAD should not change much
        assert np.isclose(mad1, mad2, rtol=0.5)


class TestTrim:
    """Tests for trim function."""

    def test_trim_by_fraction(self):
        """Test trimming by fraction."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        trimmed, _ = trim(values, fraction=0.2)
        # Should trim 1 from each end: [2, 3, 4]
        assert len(trimmed) == 3
        assert np.allclose(trimmed, [2.0, 3.0, 4.0])

    def test_trim_by_count(self):
        """Test trimming by count."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        trimmed, _ = trim(values, count=1)
        assert len(trimmed) == 3
        assert np.allclose(trimmed, [2.0, 3.0, 4.0])

    def test_trim_invalid_fraction_raises(self):
        """Test that invalid fraction raises error."""
        values = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="must be in"):
            trim(values, fraction=0.6)  # Too high


class TestWinsorize:
    """Tests for winsorize function."""

    def test_winsorize_with_limits(self):
        """Test winsorizing with explicit limits."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 100.0])
        winsorized = winsorize(values, limits=(2.0, 4.0))
        expected = np.array([2.0, 2.0, 3.0, 4.0, 4.0, 4.0])
        assert np.allclose(winsorized, expected)

    def test_winsorize_with_fraction(self):
        """Test winsorizing with quantile-based limits."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        winsorized = winsorize(values, fraction=0.2)
        # Should cap extremes (1.0 -> ~1.8, 5.0 -> ~4.2)
        assert winsorized[0] > 1.0
        assert winsorized[-1] < 5.0


class TestWeightFunctions:
    """Tests for weight functions."""

    def test_huber_weights_at_threshold(self):
        """Test Huber weights at threshold."""
        residuals = np.array([0.0, 1.345, 2.0])
        weights = huber_weights(residuals, tuning=1.345)
        assert np.isclose(weights[0], 1.0)
        assert np.isclose(weights[1], 1.0)
        assert weights[2] < 1.0  # Beyond threshold

    def test_tukey_biweight(self):
        """Test Tukey biweight weights."""
        residuals = np.array([0.0, 2.0, 5.0, 10.0])
        weights = tukey_biweight(residuals, tuning=4.685)
        assert weights[0] > 0  # Center
        assert weights[-1] == 0  # Outlier (beyond tuning * 1.0)


class TestRobustLocationScale:
    """Tests for RobustLocationScale class."""

    def test_fit_returns_self(self, contaminated_data):
        """Test that fit() returns self."""
        estimator = RobustLocationScale()
        result = estimator.fit(contaminated_data)
        assert result is estimator

    def test_robust_location_resistant_to_outliers(self, contaminated_data):
        """Test that median location is resistant to outliers."""
        estimator = RobustLocationScale()
        estimator.fit(contaminated_data)
        params = estimator.get_params()

        # Location should be close to 5.0 (center of normal data)
        # despite large outliers
        assert 4.0 < params["location"] < 6.0

    def test_get_params_before_fit_raises(self):
        """Test that get_params() before fit raises RuntimeError."""
        estimator = RobustLocationScale()
        with pytest.raises(RuntimeError, match="not yet fitted"):
            estimator.get_params()


class TestOutlierDetector:
    """Tests for OutlierDetector class."""

    def test_detect_outliers(self, contaminated_data):
        """Test outlier detection."""
        detector = OutlierDetector(threshold=2.5)
        detector.fit(contaminated_data)
        outliers = detector.detect(contaminated_data)

        # Should detect the 3 far outliers among 103 points
        assert np.sum(outliers) > 0
        assert np.sum(outliers) <= contaminated_data.n_obs

    def test_get_robust_indices(self, contaminated_data):
        """Test getting robust (non-outlier) indices."""
        detector = OutlierDetector(threshold=2.5)
        detector.fit(contaminated_data)
        robust_idx = detector.get_robust_indices(contaminated_data)

        assert len(robust_idx) > 0
        assert len(robust_idx) < contaminated_data.n_obs


class TestWeightedRobustEstimator:
    """Tests for WeightedRobustEstimator class."""

    def test_compute_weights_huber(self):
        """Test Huber weight computation."""
        estimator = WeightedRobustEstimator(weight_function="huber")
        residuals = np.array([-0.5, 0.0, 0.5, 2.0, 10.0])
        weights = estimator.compute_weights(residuals)

        # Weights should decrease for larger residuals
        assert weights[1] >= weights[2]  # Center weights higher
        assert weights[-1] < weights[0]  # Outlier weight lower

    def test_compute_weights_tukey(self):
        """Test Tukey weight computation."""
        estimator = WeightedRobustEstimator(weight_function="tukey")
        residuals = np.array([0.0, 2.0, 10.0])
        weights = estimator.compute_weights(residuals)

        assert weights[0] > 0  # Center
        assert weights[-1] == 0  # Strong outlier

    def test_fit_with_weights(self, contaminated_data):
        """Test fitting with combined weights."""
        residuals = (contaminated_data.values - 5.0) / 2.0  # Standardized
        estimator = WeightedRobustEstimator(weight_function="tukey")
        loc, scale, robust_wts = estimator.fit_with_weights(contaminated_data, residuals)

        assert loc > 0
        assert scale > 0
        assert len(robust_wts) == contaminated_data.n_obs
