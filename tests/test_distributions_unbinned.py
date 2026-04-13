"""Tests for distest.distributions module (unbinned MLE)."""

import pytest
import numpy as np
from scipy.stats import norm, expon, gamma
from distest.distributions import UnbinnedMLEEstimator


class TestUnbinnedNormal:
    """Tests for generic unbinned estimator with Normal distribution."""

    def test_fit_normal_unbinned_accuracy(self, normal_unbinned):
        """Test Normal MLE accuracy on unbinned data."""
        estimator = UnbinnedMLEEstimator(norm)
        estimator.fit(normal_unbinned)
        params = estimator.get_params()

        # Expected: mu ≈ 5.0, sigma ≈ 2.0
        assert np.isclose(params["loc"], 5.0, atol=0.2)
        assert np.isclose(params["scale"], 2.0, atol=0.3)

    def test_fit_returns_self(self, normal_unbinned):
        """Test that fit() returns self."""
        estimator = UnbinnedMLEEstimator(norm)
        result = estimator.fit(normal_unbinned)
        assert result is estimator

    def test_get_params_before_fit_raises(self):
        """Test that get_params() before fit raises RuntimeError."""
        estimator = UnbinnedMLEEstimator(norm)
        with pytest.raises(RuntimeError, match="not yet fitted"):
            estimator.get_params()

    def test_predict_likelihood(self, normal_unbinned):
        """Test predict returns log-likelihood."""
        estimator = UnbinnedMLEEstimator(norm)
        estimator.fit(normal_unbinned)
        loglik = estimator.predict(normal_unbinned)

        # Should return array of same length as data
        assert loglik.shape == (normal_unbinned.n_obs,)
        assert np.all(np.isfinite(loglik))

    def test_weighted_fit(self, rng):
        """Test fitting with weighted observations."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        weights = np.array([1.0, 1.0, 10.0, 1.0, 1.0])  # Heavy weight on 3.0
        from distest import UnbinnedData
        weighted_data = UnbinnedData(values=values, weights=weights)

        estimator = UnbinnedMLEEstimator(norm)
        estimator.fit(weighted_data)
        params = estimator.get_params()

        # Mean should be biased toward 3.0
        assert params["loc"] >= 2.8


class TestUnbinnedExponential:
    """Tests for generic unbinned estimator with Exponential distribution."""

    def test_fit_exponential_unbinned_accuracy(self, exponential_unbinned):
        """Test Exponential MLE accuracy."""
        estimator = UnbinnedMLEEstimator(expon, floc=0)
        estimator.fit(exponential_unbinned)
        params = estimator.get_params()

        # Expected: lambda = 1/scale ≈ 0.5 (since scale=2.0)
        assert np.isclose(1.0 / params["scale"], 0.5, atol=0.1)
        assert np.isclose(params["loc"], 0.0, atol=1e-8)

    def test_fit_requires_positive_values(self, rng):
        """Test that negative values raise error."""
        from distest import UnbinnedData
        values = np.array([1.0, 2.0, -3.0])
        unbinned = UnbinnedData(values=values)
        estimator = UnbinnedMLEEstimator(expon, floc=0)
        with pytest.raises(Exception):
            estimator.fit(unbinned)

    def test_get_params_before_fit_raises(self):
        """Test that get_params() before fit raises RuntimeError."""
        estimator = UnbinnedMLEEstimator(expon, floc=0)
        with pytest.raises(RuntimeError, match="not yet fitted"):
            estimator.get_params()


class TestUnbinnedGamma:
    """Tests for generic unbinned estimator with Gamma distribution."""

    def test_fit_gamma_unbinned_accuracy(self, gamma_unbinned):
        """Test Gamma MLE accuracy."""
        estimator = UnbinnedMLEEstimator(gamma, floc=0)
        estimator.fit(gamma_unbinned)
        params = estimator.get_params()

        # Expected: alpha ≈ 2.0, beta ≈ 0.5
        # (Since gamma uses shape=2, scale=2, which is alpha=2, beta=0.5)
        assert params["shape0"] > 0.5  # Rough check
        assert (1.0 / params["scale"]) > 0.1

    def test_fit_requires_positive_values(self):
        """Test that negative values raise error."""
        from distest import UnbinnedData
        values = np.array([1.0, 2.0, -3.0])
        unbinned = UnbinnedData(values=values)
        estimator = UnbinnedMLEEstimator(gamma, floc=0)
        with pytest.raises(Exception):
            estimator.fit(unbinned)

    def test_get_params_keys(self, gamma_unbinned):
        """Test that get_params returns correct keys."""
        estimator = UnbinnedMLEEstimator(gamma, floc=0)
        estimator.fit(gamma_unbinned)
        params = estimator.get_params()

        assert "shape0" in params
        assert "loc" in params
        assert "scale" in params
        assert len(params) == 3
