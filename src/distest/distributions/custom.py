"""Templates and utilities for custom distribution definition.

Provides base classes and examples for users to define custom distributions
that inherit from scipy.stats.rv_continuous.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.stats import rv_continuous

from ..core import BaseEstimator, HistogramData, UnbinnedData
from .scipy_ext import MLEOptimizer


class CustomRVContinuous(rv_continuous):
    """Base class for custom continuous distributions.

    Users should subclass this and implement the pdf/cdf/logpdf methods.

    Example:
        class MyDistribution(CustomRVContinuous):
            def _pdf(self, x, param1, param2):
                # Your PDF implementation
                ...

            def _cdf(self, x, param1, param2):
                # Your CDF implementation
                ...
    """

    pass


class CustomUnbinnedEstimator(BaseEstimator):
    """Template for custom MLE estimator on unbinned data.

    Users implement:
    - logpdf_func: Computes log-PDF given (values, params)
    - initial_params: Initial parameter guess function
    - param_bounds: Bounds for scipy.optimize
    """

    def __init__(
        self,
        logpdf_func: callable,
        initial_params_func: callable,
        param_names: list[str],
        bounds: list[tuple[float | None, float | None]] | None = None,
    ) -> None:
        """Initialize custom unbinned estimator.

        Args:
            logpdf_func: Function(values: ndarray, params: ndarray) -> log-pdf array.
            initial_params_func: Function(values, weights) -> initial params array.
            param_names: Names of parameters (for get_params() dict).
            bounds: Optional bounds for each parameter [(low, high), ...].
        """
        self.logpdf_func = logpdf_func
        self.initial_params_func = initial_params_func
        self.param_names = param_names
        self.bounds = bounds or [(None, None)] * len(param_names)
        self.params_: NDArray | None = None
        self._optimizer = MLEOptimizer()

    def fit(self, data: UnbinnedData) -> CustomUnbinnedEstimator:
        """Fit custom distribution to unbinned data.

        Args:
            data: UnbinnedData instance.

        Returns:
            self: Fitted estimator.

        Raises:
            ValueError: If fitting fails.
        """
        values = data.values
        weights = data.weights

        # Get initial guess
        params_init = self.initial_params_func(values, weights)

        # Define negative log-likelihood
        def neg_loglik(params: NDArray) -> float:
            try:
                logpdf = self.logpdf_func(values, params)
                if not np.all(np.isfinite(logpdf)):
                    return 1e308
                return float(-np.sum(weights * logpdf))
            except Exception:
                return 1e308

        # Optimize
        try:
            params_opt, _ = self._optimizer.minimize_neg_loglik(
                neg_loglik, params_init, bounds=self.bounds
            )
            self.params_ = params_opt
        except RuntimeError as e:
            raise ValueError(f"MLE fitting failed: {e}") from e

        return self

    def get_params(self) -> dict[str, float]:
        """Get fitted parameters.

        Returns:
            Dictionary mapping param_names to fitted values.

        Raises:
            RuntimeError: If called before fit().
        """
        if self.params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")
        return {name: float(val) for name, val in zip(self.param_names, self.params_)}

    def predict(self, data: UnbinnedData) -> NDArray:
        """Compute log-likelihood.

        Args:
            data: UnbinnedData instance.

        Returns:
            Log-likelihood array.
        """
        if self.params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")
        return self.logpdf_func(data.values, self.params_)


class CustomBinnedEstimator(BaseEstimator):
    """Template for custom MLE estimator on binned data.

    Users implement:
    - cdf_func: Computes CDF given (x, params)
    - initial_params: Initial parameter guess function
    - param_bounds: Bounds for scipy.optimize
    """

    def __init__(
        self,
        cdf_func: callable,
        initial_params_func: callable,
        param_names: list[str],
        bounds: list[tuple[float | None, float | None]] | None = None,
    ) -> None:
        """Initialize custom binned estimator.

        Args:
            cdf_func: Function(x: ndarray, params: ndarray) -> CDF array.
            initial_params_func: Function(histogram_data) -> initial params array.
            param_names: Names of parameters.
            bounds: Optional bounds [(low, high), ...].
        """
        self.cdf_func = cdf_func
        self.initial_params_func = initial_params_func
        self.param_names = param_names
        self.bounds = bounds or [(None, None)] * len(param_names)
        self.params_: NDArray | None = None
        self._optimizer = MLEOptimizer()

    def fit(self, data: HistogramData) -> CustomBinnedEstimator:
        """Fit custom distribution to binned data.

        Args:
            data: HistogramData instance.

        Returns:
            self: Fitted estimator.

        Raises:
            ValueError: If fitting fails.
        """
        # Get initial guess
        params_init = self.initial_params_func(data)

        # Define negative log-likelihood
        def neg_loglik(params: NDArray) -> float:
            try:
                cdf = self.cdf_func(data.edges, params)
                if not np.all(np.isfinite(cdf)):
                    return 1e308
                bin_probs = np.diff(cdf)
                if not np.all(bin_probs > 0):
                    return 1e308
                loglik = np.sum(
                    data.weights * data.counts * np.log(bin_probs)
                )
                return float(-loglik)
            except Exception:
                return 1e308

        # Optimize
        try:
            params_opt, _ = self._optimizer.minimize_neg_loglik(
                neg_loglik, params_init, bounds=self.bounds
            )
            self.params_ = params_opt
        except RuntimeError as e:
            raise ValueError(f"MLE fitting failed: {e}") from e

        return self

    def get_params(self) -> dict[str, float]:
        """Get fitted parameters.

        Returns:
            Dictionary mapping param_names to fitted values.

        Raises:
            RuntimeError: If called before fit().
        """
        if self.params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")
        return {name: float(val) for name, val in zip(self.param_names, self.params_)}

    def predict(self, data: HistogramData) -> NDArray:
        """Compute log-probability for bins.

        Args:
            data: HistogramData instance.

        Returns:
            Log-probability array (one per bin).
        """
        if self.params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")
        cdf = self.cdf_func(data.edges, self.params_)
        bin_probs = np.diff(cdf)
        return np.log(np.maximum(bin_probs, 1e-300))


__all__ = [
    "CustomRVContinuous",
    "CustomUnbinnedEstimator",
    "CustomBinnedEstimator",
]
