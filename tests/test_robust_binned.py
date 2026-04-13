"""Tests for distest.robust module (binned)."""

import pytest
import numpy as np
from distest.robust import (
    RobustLocationScaleBinned, BinnedOutlierDetector, RobustHistogramWeights,
)
from distest import HistogramData


class TestRobustLocationScaleBinned:
    """Tests for RobustLocationScaleBinned class."""

    def test_fit_returns_self(self, normal_binned):
        """Test that fit() returns self."""
        estimator = RobustLocationScaleBinned()
        result = estimator.fit(normal_binned)
        assert result is estimator

    def test_location_estimation(self, normal_binned):
        """Test location estimation from histogram."""
        estimator = RobustLocationScaleBinned()
        estimator.fit(normal_binned)
        params = estimator.get_params()

        # Expected: location ≈ 5.0
        assert 4.5 < params["location"] < 5.5

    def test_scale_estimation(self, normal_binned):
        """Test scale estimation from histogram."""
        estimator = RobustLocationScaleBinned()
        estimator.fit(normal_binned)
        params = estimator.get_params()

        # Expected: scale > 0
        assert params["scale"] > 0

    def test_get_params_before_fit_raises(self):
        """Test that get_params() before fit raises RuntimeError."""
        estimator = RobustLocationScaleBinned()
        with pytest.raises(RuntimeError, match="not yet fitted"):
            estimator.get_params()

    def test_with_weighted_histogram(self):
        """Test robust estimation with weighted bins."""
        edges = np.linspace(0, 10, 11)
        counts = np.array([5, 10, 20, 30, 35, 30, 20, 10, 5, 2])
        weights = np.array([1.0] * 10)
        hist = HistogramData(edges=edges, counts=counts, weights=weights)

        estimator = RobustLocationScaleBinned()
        estimator.fit(hist)
        params = estimator.get_params()

        assert 4.0 < params["location"] < 6.0
        assert params["scale"] > 0


class TestBinnedOutlierDetector:
    """Tests for BinnedOutlierDetector class."""

    def test_fit_returns_self(self, normal_binned):
        """Test that fit() returns self."""
        detector = BinnedOutlierDetector()
        result = detector.fit(normal_binned)
        assert result is detector

    def test_detect_outlier_bins(self):
        """Test detection of outlier bins."""
        # Create histogram with outlier bin
        edges = np.linspace(0, 100, 11)
        counts = np.array([5, 10, 20, 30, 35, 30, 20, 10, 5, 500])  # Large count in last bin
        hist = HistogramData(edges=edges, counts=counts)

        detector = BinnedOutlierDetector(threshold=2.0)
        detector.fit(hist)
        outliers = detector.detect(hist)

        # Should flag high-value bins as outliers
        assert np.any(outliers)

    def test_outlier_detection_returns_boolean_array(self, normal_binned):
        """Test that detect returns boolean array of correct shape."""
        detector = BinnedOutlierDetector()
        detector.fit(normal_binned)
        outliers = detector.detect(normal_binned)

        assert outliers.dtype == bool
        assert outliers.shape == (normal_binned.n_bins,)


class TestRobustHistogramWeights:
    """Tests for RobustHistogramWeights class."""

    def test_compute_weights_default_location_scale(self, normal_binned):
        """Test weight computation with default location and scale."""
        weight_comp = RobustHistogramWeights(method="huber")
        weights = weight_comp.compute_weights(normal_binned)

        # Weights should be in [0, 1]
        assert np.all(weights >= 0)
        assert np.all(weights <= 1)
        assert weights.shape == (normal_binned.n_bins,)

    def test_compute_weights_with_location_scale(self, normal_binned):
        """Test weight computation with custom location and scale."""
        weight_comp = RobustHistogramWeights(method="tukey")
        weights = weight_comp.compute_weights(
            normal_binned,
            location=5.0,
            scale=2.0,
        )

        assert np.all(weights >= 0)
        assert np.all(weights <= 1)

    def test_compute_weights_huber_method(self, normal_binned):
        """Test Huber weight method."""
        weight_comp = RobustHistogramWeights(method="huber")
        weights = weight_comp.compute_weights(normal_binned, location=5.0, scale=1.0)

        # Center bins should have weight close to 1
        center_idx = normal_binned.n_bins // 2
        assert weights[center_idx] > 0.5

    def test_compute_weights_tukey_method(self, normal_binned):
        """Test Tukey biweight method."""
        weight_comp = RobustHistogramWeights(method="tukey")
        weights = weight_comp.compute_weights(normal_binned, location=5.0, scale=1.0)

        # Extreme bins should have zero (or very small) weights
        assert np.any(weights == 0.0) or np.all(weights > 0)

    def test_compute_weights_unknown_method_raises(self, normal_binned):
        """Test that unknown method raises ValueError."""
        weight_comp = RobustHistogramWeights(method="unknown_method")
        with pytest.raises(ValueError, match="Unknown method"):
            weight_comp.compute_weights(normal_binned)
