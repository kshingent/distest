"""Maximum likelihood estimation for binned (histogram) data.

Uses scipy.stats.rv_continuous CDF and generic optimization.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import rv_continuous

from ..core import BaseEstimator, HistogramData
from .scipy_ext import MLEOptimizer, estimate_binned_initial_params


class BinnedMLEEstimator(BaseEstimator):
    """Generic binned-data MLE estimator for scipy rv_continuous distributions.

    Args:
        dist: A scipy.stats rv_continuous instance.
        support_min: Optional lower support bound for edges (e.g. 0 for expon/gamma).
        **fit_kwargs: Passed to dist.fit() for initialization (e.g. floc=0).
    """

    def __init__(
        self,
        dist: rv_continuous,
        support_min: float | None = None,
        **fit_kwargs: float,
    ) -> None:
        self.dist = dist
        self.support_min = support_min
        self.fit_kwargs = fit_kwargs
        self.fitted_params_: tuple[float, ...] | None = None
        self._optimizer = MLEOptimizer()

    def fit(self, data: HistogramData) -> BinnedMLEEstimator:
        if self.support_min is not None and not np.all(data.edges >= self.support_min):
            raise ValueError(f"All bin edges must be >= {self.support_min}")

        init_params = estimate_binned_initial_params(self.dist, data, **self.fit_kwargs)
        self.fitted_params_ = self._optimize_binned(data, init_params)
        return self

    def _optimize_binned(
        self,
        data: HistogramData,
        init_params: np.ndarray,
    ) -> tuple[float, ...]:
        n = self.dist.numargs
        total = n + 2  # shapes + loc + scale

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
            if i == n:
                return (None, None)  # loc
            if i == n + 1:
                return (1e-6, None)  # scale
            return (None, None)      # shape params: distribution decides validity

        bounds = [bounds_for(i) for i in free_idx]

        def neg_loglik(free_params: np.ndarray) -> float:
            p = list(init_params)
            for i, idx in enumerate(free_idx):
                p[idx] = free_params[i]
            for idx, val in fixed.items():
                p[idx] = val

            cdf = self.dist.cdf(data.edges, *p[:n], loc=p[n], scale=p[n + 1])
            if not np.all(np.isfinite(cdf)):
                return 1e308

            bin_probs = np.diff(cdf)
            if not np.all(bin_probs > 0):
                return 1e308

            loglik = np.sum(data.weights * data.counts * np.log(bin_probs))
            return float(-loglik)

        free_opt, _ = self._optimizer.minimize_neg_loglik(
            neg_loglik, init_free, bounds=bounds
        )

        p = list(init_params)
        for i, idx in enumerate(free_idx):
            p[idx] = free_opt[i]
        for idx, val in fixed.items():
            p[idx] = val
        return tuple(float(x) for x in p)

    def get_params(self) -> dict[str, float]:
        if self.fitted_params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")

        n = self.dist.numargs
        params: dict[str, float] = {
            f"shape{i}": float(self.fitted_params_[i]) for i in range(n)
        }
        params["loc"] = float(self.fitted_params_[n])
        params["scale"] = float(self.fitted_params_[n + 1])
        return params

    def predict(self, data: HistogramData) -> np.ndarray:
        if self.fitted_params_ is None:
            raise RuntimeError("Model not yet fitted. Call fit() first.")

        n = self.dist.numargs
        p = self.fitted_params_
        cdf = self.dist.cdf(data.edges, *p[:n], loc=p[n], scale=p[n + 1])
        bin_probs = np.diff(cdf)
        return np.log(np.maximum(bin_probs, 1e-300))


__all__ = ["BinnedMLEEstimator"]
