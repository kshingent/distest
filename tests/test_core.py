"""Tests for distest.core module."""

import pytest
import numpy as np
from distest import HistogramData, UnbinnedData, validate_weights, is_numeric_stable


class TestHistogramData:
    """Tests for HistogramData class."""

    def test_init_valid(self):
        """Test valid HistogramData initialization."""
        edges = np.array([0.0, 1.0, 2.0, 3.0])
        counts = np.array([10.0, 20.0, 15.0])
        hist = HistogramData(edges=edges, counts=counts)
        assert hist.n_bins == 3
        assert hist.total_count == 45.0
        assert np.allclose(hist.centers, [0.5, 1.5, 2.5])
        assert np.allclose(hist.bin_widths, [1.0, 1.0, 1.0])

    def test_init_with_weights(self):
        """Test HistogramData with weights."""
        edges = np.array([0.0, 1.0, 2.0])
        counts = np.array([10.0, 20.0])
        weights = np.array([1.0, 2.0])
        hist = HistogramData(edges=edges, counts=counts, weights=weights)
        assert np.allclose(hist.weights, weights)

    def test_init_invalid_edges_not_increasing(self):
        """Test that invalid (non-increasing) edges raises error."""
        edges = np.array([0.0, 2.0, 1.0])
        counts = np.array([10.0, 20.0])
        with pytest.raises(ValueError, match="strictly increasing"):
            HistogramData(edges=edges, counts=counts)

    def test_init_invalid_counts_length(self):
        """Test that mismatched counts length raises error."""
        edges = np.array([0.0, 1.0, 2.0, 3.0])
        counts = np.array([10.0, 20.0])  # Too short
        with pytest.raises(ValueError, match="counts length"):
            HistogramData(edges=edges, counts=counts)

    def test_init_negative_counts(self):
        """Test that negative counts raises error."""
        edges = np.array([0.0, 1.0, 2.0])
        counts = np.array([10.0, -5.0])
        with pytest.raises(ValueError, match="non-negative"):
            HistogramData(edges=edges, counts=counts)

    def test_init_custom_centers(self):
        """Test HistogramData with custom centers."""
        edges = np.array([0.0, 1.0, 2.0])
        counts = np.array([10.0, 20.0])
        centers = np.array([0.3, 1.7])
        hist = HistogramData(edges=edges, counts=counts, centers=centers)
        assert np.allclose(hist.centers, centers)


class TestUnbinnedData:
    """Tests for UnbinnedData class."""

    def test_init_valid(self):
        """Test valid UnbinnedData initialization."""
        values = np.array([1.5, 2.3, 0.8, 3.1, 2.0])
        unbinned = UnbinnedData(values=values)
        assert unbinned.n_obs == 5
        assert unbinned.total_weight == 5.0
        assert np.isclose(unbinned.effective_sample_size, 5.0)

    def test_init_with_weights(self):
        """Test UnbinnedData with weights."""
        values = np.array([1.0, 2.0, 3.0])
        weights = np.array([1.0, 2.0, 1.0])
        unbinned = UnbinnedData(values=values, weights=weights)
        assert unbinned.total_weight == 4.0
        assert unbinned.effective_sample_size > 0

    def test_init_invalid_weights_length(self):
        """Test that mismatched weights length raises error."""
        values = np.array([1.0, 2.0, 3.0])
        weights = np.array([1.0, 2.0])  # Too short
        with pytest.raises(ValueError, match="weights length"):
            UnbinnedData(values=values, weights=weights)

    def test_init_negative_weights(self):
        """Test that negative weights raise error."""
        values = np.array([1.0, 2.0, 3.0])
        weights = np.array([1.0, -2.0, 1.0])
        with pytest.raises(ValueError, match="strictly positive"):
            UnbinnedData(values=values, weights=weights)

    def test_init_empty_values(self):
        """Test that empty values raise error."""
        with pytest.raises(ValueError, match="at least one element"):
            UnbinnedData(values=np.array([]))


class TestValidationFunctions:
    """Tests for validation utility functions."""

    def test_validate_weights_none(self):
        """Test that None weights returns uniform."""
        weights = validate_weights(None, n=5)
        assert np.allclose(weights, np.ones(5))

    def test_validate_weights_valid(self):
        """Test valid weights."""
        w = np.array([1.0, 2.0, 3.0])
        result = validate_weights(w, n=3)
        assert np.allclose(result, w)

    def test_validate_weights_invalid_shape(self):
        """Test invalid weights shape."""
        w = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="shape"):
            validate_weights(w, n=3)

    def test_validate_weights_negative(self):
        """Test negative weights."""
        w = np.array([1.0, -2.0, 1.0])
        with pytest.raises(ValueError, match="strictly positive"):
            validate_weights(w, n=3)


class TestNumericStability:
    """Tests for numeric stability checker."""

    def test_stable_values(self):
        """Test stable values."""
        values = np.array([1.0, 2.0, 3.0, 100.0])
        assert is_numeric_stable(values)

    def test_inf_values(self):
        """Test inf values."""
        values = np.array([1.0, np.inf, 3.0])
        assert not is_numeric_stable(values)

    def test_nan_values(self):
        """Test NaN values."""
        values = np.array([1.0, np.nan, 3.0])
        assert not is_numeric_stable(values)

    def test_extreme_values(self):
        """Test extreme (subnormal) values."""
        tiny = np.finfo(np.float64).tiny  # ~2.2e-308
        subnormal = tiny * 1e-10          # ~2.2e-318, subnormal but non-zero
        values = np.array([1.0, subnormal, 3.0])
        # subnormal is below min_val=1e-300, so should be unstable
        result = is_numeric_stable(values, min_val=1e-300)
        assert not result
