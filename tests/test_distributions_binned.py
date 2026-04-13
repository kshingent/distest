"""Tests for distest.distributions module (binned MLE)."""

import pytest
import numpy as np
from scipy.stats import expon, gamma, norm

from distest.distributions import BinnedMLEEstimator


class TestBinnedNormal:
    """Tests for generic binned estimator with Normal distribution."""

    def test_fit_normal_binned_accuracy(self, normal_binned):
        """Test Normal MLE accuracy on binned data."""
        estimator = BinnedMLEEstimator(norm)
        estimator.fit(normal_binned)
        params = estimator.get_params()

        # Expected: mu ≈ 5.0, sigma ≈ 2.0
        assert np.isclose(params["loc"], 5.0, atol=0.3)
        assert np.isclose(params["scale"], 2.0, atol=0.5)

    def test_fit_returns_self(self, normal_binned):
        """Test that fit() returns self."""
        estimator = BinnedMLEEstimator(norm)
        result = estimator.fit(normal_binned)
        assert result is estimator

    def test_get_params_before_fit_raises(self):
        """Test that get_params() before fit raises RuntimeError."""
        estimator = BinnedMLEEstimator(norm)
        with pytest.raises(RuntimeError, match="not yet fitted"):
            estimator.get_params()

    def test_predict_log_probability(self, normal_binned):
        """Test predict returns log-probability per bin."""
        estimator = BinnedMLEEstimator(norm)
        estimator.fit(normal_binned)
        logprob = estimator.predict(normal_binned)

        # Should return array of same length as bins
        assert logprob.shape == (normal_binned.n_bins,)
        assert np.all(np.isfinite(logprob))

    def test_weighted_fit(self):
        """Test fitting with weighted histogram bins."""
        from distest import HistogramData
        edges = np.linspace(0, 10, 11)
        counts = np.array([10, 20, 30, 25, 15, 10, 8, 5, 3, 2])
        weights = np.array([1.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        hist = HistogramData(edges=edges, counts=counts, weights=weights)

        estimator = BinnedMLEEstimator(norm)
        estimator.fit(hist)
        params = estimator.get_params()
        assert params["scale"] > 0


class TestBinnedExponential:
    """Tests for generic binned estimator with Exponential distribution."""

    def test_fit_exponential_binned_accuracy(self, exponential_binned):
        """Test Exponential MLE accuracy on binned data."""
        estimator = BinnedMLEEstimator(expon, support_min=0.0, floc=0)
        estimator.fit(exponential_binned)
        params = estimator.get_params()

        # Expected: lambda ≈ 0.5
        assert np.isclose(1.0 / params["scale"], 0.5, atol=0.15)

    def test_fit_requires_positive_edges(self):
        """Test that negative edges raise error."""
        from distest import HistogramData
        edges = np.array([-1.0, 0.0, 1.0, 2.0])  # strictly increasing, but < 0
        counts = np.array([10.0, 20.0, 15.0])
        hist = HistogramData(edges=edges, counts=counts)

        estimator = BinnedMLEEstimator(expon, support_min=0.0, floc=0)
        with pytest.raises(ValueError, match=">= 0"):
            estimator.fit(hist)

    def test_get_params_before_fit_raises(self):
        """Test that get_params() before fit raises RuntimeError."""
        estimator = BinnedMLEEstimator(expon, support_min=0.0, floc=0)
        with pytest.raises(RuntimeError, match="not yet fitted"):
            estimator.get_params()


class TestBinnedGamma:
    """Tests for generic binned estimator with Gamma distribution."""

    def test_fit_gamma_binned_accuracy(self, gamma_binned):
        """Test Gamma MLE accuracy on binned data."""
        estimator = BinnedMLEEstimator(gamma, support_min=0.0, floc=0)
        estimator.fit(gamma_binned)
        params = estimator.get_params()

        # Simple check: parameters should be positive
        assert params["shape0"] > 0
        assert (1.0 / params["scale"]) > 0

    def test_fit_requires_positive_edges(self):
        """Test that negative edges raise error."""
        from distest import HistogramData
        edges = np.array([-1.0, 0.0, 1.0, 2.0])  # strictly increasing, but < 0
        counts = np.array([10.0, 20.0, 15.0])
        hist = HistogramData(edges=edges, counts=counts)

        estimator = BinnedMLEEstimator(gamma, support_min=0.0, floc=0)
        with pytest.raises(ValueError, match=">= 0"):
            estimator.fit(hist)

    def test_get_params_keys(self, gamma_binned):
        """Test that get_params returns correct keys."""
        estimator = BinnedMLEEstimator(gamma, support_min=0.0, floc=0)
        estimator.fit(gamma_binned)
        params = estimator.get_params()

        assert "shape0" in params
        assert "loc" in params
        assert "scale" in params
        assert len(params) == 3
