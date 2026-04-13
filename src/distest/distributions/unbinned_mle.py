"""Maximum likelihood estimation for unbinned (raw) data.

Uses scipy.stats.rv_continuous.fit() as the canonical MLE solver.
For weighted data, falls back to scipy.optimize but still delegates all
distribution math to rv_continuous.logpdf() -- no distribution-specific code.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import rv_continuous

from ..core import BaseEstimator, UnbinnedData
from .scipy_ext import MLEOptimizer


class UnbinnedMLEEstimator(BaseEstimator):
    """Generic MLE estimator for any scipy.stats rv_continuous distribution.

    Fitting strategy:
    - Uniform weights: delegates directly to rv_continuous.fit() (MLE).
    - Non-uniform weights: uses rv_continuous.fit() for the initial guess,
      then refines with scipy.optimize using rv_continuous.logpdf() generically.

    Args:
        dist: A scipy.stats rv_continuous instance.
        **fit_kwargs: Passed to dist.fit() to fix parameters (e.g. floc=0).
    """

    def __init__(self, dist: rv_continuous, **fit_kwargs: float) -> None:
        self.dist = dist
        self.fit_kwargs = fit_kwargs
        self.fitted_params_: tuple[float, ...] | None = None

    def fit(self, data: UnbinnedData) -> UnbinnedMLEEstimator:
        values = data.values
        weights = data.weights

        w = weights / weights.sum()
        if np.allclose(w, w[0]):
            self.fitted_params_ = tuple(
                float(p) for p in self.dist.fit(values, **self.fit_kwargs)
            )
        else:
            init = np.array(self.dist.fit(values, **self.fit_kwargs), dtype=float)
            self.fitted_params_ = self._weighted_fit(values, weights, init)

        return self

    def _weighted_fit(
        self,
        values: np.ndarray,
        weights: np.ndarray,
        init_params: np.ndarray,
    ) -> tuple[float, ...]:
        """Weighted MLE via numerical optimization.

        Uses rv_continuous.logpdf() generically -- no distribution-specific math.
        """
        n = self.dist.numargs  # number of shape parameters
        total = n + 2          # shapes + loc + scale

        fixed: dict[int, float] = {}
        for key, val in self.fit_kwargs.items():
            if key == "floc":
                fixed[n] = float(val)
            elif key == "fscale":
                fixed[n + 1] = float(val)
            elif key.startswith("f") and key[1:].isdigit():
                fixed[int(key[1:])] = float(val)

        free_idx = [i for i in range(total) if i not in fixed]
        init_free = init_params[free_idx]

        def bounds_for(i: int) -> tuple[float | None, float | None]:
            return (None, None) if i == n else (1e-6, None)

        bounds = [bounds_for(i) for i in free_idx]

        def neg_loglik(free_params: np.ndarray) -> float:
            p = list(init_params)
            for i, idx in enumerate(free_idx):
                p[idx] = free_params[i]
            for idx, val in fixed.items():
                p[idx] = val
            lp = self.dist.logpdf(values, *p[:n], loc=p[n], scale=p[n + 1])
            if not np.all(np.isfinite(lp)):
                return 1e308
            return float(-np.sum(weights * lp))

        result_free, _ = MLEOptimizer().minimize_neg_loglik(
            neg_loglik, init_free, bounds=bounds
        )

        p = list(init_params)
        for i, idx in enumerate(free_idx):
            p[idx] = result_free[i]
        for idx, val in fixed.items():
            p[idx] = val
        return tuple(float(x) for x in p)

    def predict(self, data: UnbinnedData) -> np.ndarray:
        """Return log-pdf array for each observation."""
        if self.fitted_params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")
        n = self.dist.numargs
        p = self.fitted_params_
        return self.dist.logpdf(data.values, *p[:n], loc=p[n], scale=p[n + 1])


    def get_params(self) -> dict[str, float]:
        """Return fitted parameters in a generic, distribution-agnostic format.

        Keys are "shape0", "shape1", ..., "loc", and "scale".
        """
        if self.fitted_params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")

        n = self.dist.numargs
        params: dict[str, float] = {
            f"shape{i}": float(self.fitted_params_[i]) for i in range(n)
        }
        params["loc"] = float(self.fitted_params_[n])
        params["scale"] = float(self.fitted_params_[n + 1])
        return params


__all__ = [
    "UnbinnedMLEEstimator",
]
