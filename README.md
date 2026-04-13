# distest

distest is a statistical estimation library for two common data shapes:

- Unbinned data: raw observation arrays
- Binned data: histogram counts and bin edges

It provides a consistent API to estimate distribution parameters with maximum
likelihood and to compute robust statistics that are less sensitive to outliers.

## Features

- Distribution estimation (`distest.distributions`)
	- `UnbinnedMLEEstimator`: generic MLE for raw arrays using `scipy.stats`
	- `BinnedMLEEstimator`: generic MLE for histogram data via bin probabilities
	- Custom estimator templates for user-defined distributions
- Robust statistics (`distest.robust`)
	- Location/scale estimators for unbinned and binned data
	- Outlier detection utilities
	- Trimming, winsorizing, Huber and Tukey weight functions

## When To Use

- You have sample arrays and want MLE parameters from a SciPy distribution.
- You only have histogram counts/edges and still want MLE fitting.
- You need median/MAD-style robust summaries under outlier contamination.
- You want to build custom distribution estimators with shared optimization logic.

## Requirements

- Python 3.10+
- NumPy 1.20+
- SciPy 1.7+

## Installation

```bash
uv sync --group dev
```

If you only need runtime dependencies (without dev tools), use:

```bash
uv sync
```

## Quick Start

### 1) Unbinned MLE (raw observations)

```python
import numpy as np
from scipy.stats import norm

from distest import UnbinnedData
from distest.distributions import UnbinnedMLEEstimator

rng = np.random.default_rng(42)
values = rng.normal(loc=5.0, scale=2.0, size=500)

data = UnbinnedData(values=values)
est = UnbinnedMLEEstimator(norm).fit(data)
print(est.get_params())
# Example: {'loc': 4.97..., 'scale': 1.98...}
```

### 2) Binned MLE (histogram)

```python
import numpy as np
from scipy.stats import norm

from distest import HistogramData
from distest.distributions import BinnedMLEEstimator

rng = np.random.default_rng(42)
values = rng.normal(loc=5.0, scale=2.0, size=500)

edges = np.linspace(0, 10, 21)
counts, _ = np.histogram(values, bins=edges)

hist = HistogramData(edges=edges, counts=counts)
est = BinnedMLEEstimator(norm).fit(hist)
print(est.get_params())
```

### 3) Robust location and scale

```python
import numpy as np
from distest import UnbinnedData
from distest.robust import RobustLocationScale

rng = np.random.default_rng(42)
values = np.concatenate([
		rng.normal(5.0, 2.0, 100),
		np.array([50.0, -50.0, 100.0]),
])

data = UnbinnedData(values=values)
robust = RobustLocationScale().fit(data)
print(robust.get_params())
# Example: {'location': 5.1..., 'scale': 3.0...}
```

## API Overview

Top-level data containers (`distest`):

- `UnbinnedData`
- `HistogramData`

Distribution estimation (`distest.distributions`):

- `UnbinnedMLEEstimator`
- `BinnedMLEEstimator`
- `CustomRVContinuous`
- `CustomUnbinnedEstimator`
- `CustomBinnedEstimator`

Robust statistics (`distest.robust`):

- `RobustLocationScale`, `RobustStandardization`, `OutlierDetector`
- `RobustLocationScaleBinned`, `BinnedOutlierDetector`, `RobustHistogramWeights`
- `median`, `mad`, `trim`, `winsorize`, `huber_weights`, `tukey_biweight`

## Custom Estimator Minimal Example

### Custom unbinned estimator (logpdf-based)

```python
import numpy as np
from scipy.stats import norm

from distest import UnbinnedData
from distest.distributions import CustomUnbinnedEstimator


def logpdf_func(values: np.ndarray, params: np.ndarray) -> np.ndarray:
	loc, scale = params
	return norm.logpdf(values, loc=loc, scale=scale)


def initial_params(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
	loc0 = float(np.average(values, weights=weights))
	var0 = float(np.average((values - loc0) ** 2, weights=weights))
	return np.array([loc0, np.sqrt(max(var0, 1e-8))], dtype=float)


data = UnbinnedData(values=np.random.default_rng(0).normal(2.0, 1.5, 300))

est = CustomUnbinnedEstimator(
	logpdf_func=logpdf_func,
	initial_params_func=initial_params,
	param_names=["loc", "scale"],
	bounds=[(None, None), (1e-6, None)],
).fit(data)

print(est.get_params())
```

### Custom binned estimator (cdf-based)

```python
import numpy as np
from scipy.stats import norm

from distest import HistogramData
from distest.distributions import CustomBinnedEstimator


def cdf_func(x: np.ndarray, params: np.ndarray) -> np.ndarray:
	loc, scale = params
	return norm.cdf(x, loc=loc, scale=scale)


def initial_params(hist: HistogramData) -> np.ndarray:
	loc0 = float(np.average(hist.centers, weights=hist.counts))
	var0 = float(np.average((hist.centers - loc0) ** 2, weights=hist.counts))
	return np.array([loc0, np.sqrt(max(var0, 1e-8))], dtype=float)


rng = np.random.default_rng(0)
values = rng.normal(2.0, 1.5, 300)
edges = np.linspace(-4, 8, 25)
counts, _ = np.histogram(values, bins=edges)

hist = HistogramData(edges=edges, counts=counts)

est = CustomBinnedEstimator(
	cdf_func=cdf_func,
	initial_params_func=initial_params,
	param_names=["loc", "scale"],
	bounds=[(None, None), (1e-6, None)],
).fit(hist)

print(est.get_params())
```

## Development

Run tests:

```bash
uv run pytest tests/ -q
```

Run tests with coverage:

```bash
uv run pytest tests/ --cov=src/distest --cov-report=term-missing -q
```

Type check:

```bash
uv run mypy src tests
```

Lint:

```bash
uv run ruff check .
```

## Project Layout

```text
src/distest/
	core.py                # shared containers and base interfaces
	distributions/         # unbinned/binned MLE estimators
	robust/                # robust statistics and outlier utilities
tests/                   # pytest suite
```

## License

MIT
