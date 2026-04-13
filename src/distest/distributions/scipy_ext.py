"""Scipy integration utilities for binned MLE optimization."""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize
from scipy.stats import rv_continuous

from ..core import HistogramData


class MLEOptimizer:
    """Numerical MLE optimizer for binned data.

    Scipy's rv_continuous.fit() does not support binned histograms, so
    binned MLE uses scipy.optimize.minimize via this class.
    """

    def __init__(
        self,
        method: str = "L-BFGS-B",
        tol: float = 1e-6,
        max_iter: int = 10000,
    ) -> None:
        self.method = method
        self.tol = tol
        self.max_iter = max_iter

    def minimize_neg_loglik(
        self,
        neg_loglik_func: Callable[[NDArray], float],
        initial_params: NDArray,
        bounds: Optional[list[tuple[float, float]]] = None,
    ) -> tuple[NDArray, float]:
        """Minimize negative log-likelihood and return (params, neg_loglik).

        Raises:
            RuntimeError: If optimization fails to converge.
        """
        result = minimize(
            neg_loglik_func,
            initial_params,
            method=self.method,
            bounds=bounds,
            options={"maxiter": self.max_iter, "ftol": self.tol},
        )
        if not result.success:
            raise RuntimeError(f"MLE optimization failed: {result.message}")
        return result.x, float(result.fun)


def histogram_to_pseudo_sample(
    hist_data: HistogramData,
    max_size: int = 20000,
) -> NDArray[np.float64]:
    """Create pseudo-samples from histogram centers for rv_continuous.fit().

    The sample size is capped to keep initialization fast while preserving
    relative mass across bins.
    """
    masses = np.asarray(hist_data.weights * hist_data.counts, dtype=float)
    if np.any(masses < 0):
        raise ValueError("Histogram masses must be non-negative")

    total_mass = float(np.sum(masses))
    if total_mass <= 0:
        raise ValueError("Histogram mass must be positive")

    scale = min(1.0, max_size / total_mass)
    repeats = np.rint(masses * scale).astype(int)
    repeats[(masses > 0) & (repeats == 0)] = 1

    sample = np.repeat(hist_data.centers, repeats)
    if sample.size == 0:
        raise ValueError("Failed to create pseudo-sample from histogram")
    return np.asarray(sample, dtype=float)


def estimate_binned_initial_params(
    dist: rv_continuous,
    hist_data: HistogramData,
    **fit_kwargs: float,
) -> NDArray[np.float64]:
    """Estimate initial parameters for binned MLE using rv_continuous.fit()."""
    pseudo_sample = histogram_to_pseudo_sample(hist_data)
    fitted = dist.fit(pseudo_sample, **fit_kwargs)
    return np.asarray(fitted, dtype=float)


__all__ = [
    "MLEOptimizer",
    "histogram_to_pseudo_sample",
    "estimate_binned_initial_params",
]
