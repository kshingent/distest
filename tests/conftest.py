"""pytest configuration and fixtures for distest tests."""

import pytest
import numpy as np
from distest import HistogramData, UnbinnedData


@pytest.fixture
def rng():
    """Seeded random number generator."""
    return np.random.RandomState(42)


@pytest.fixture
def normal_unbinned(rng):
    """Generate normal unbinned data."""
    values = rng.normal(loc=5.0, scale=2.0, size=500)
    return UnbinnedData(values=values)


@pytest.fixture
def normal_binned(rng):
    """Generate normal binned data (histogram)."""
    values = rng.normal(loc=5.0, scale=2.0, size=500)
    edges = np.linspace(0, 10, 21)
    counts, _ = np.histogram(values, bins=edges)
    return HistogramData(edges=edges, counts=counts)


@pytest.fixture
def exponential_unbinned(rng):
    """Generate exponential unbinned data."""
    values = rng.exponential(scale=2.0, size=500)
    return UnbinnedData(values=values)


@pytest.fixture
def exponential_binned(rng):
    """Generate exponential binned data."""
    values = rng.exponential(scale=2.0, size=500)
    edges = np.linspace(0, 15, 31)
    counts, _ = np.histogram(values, bins=edges)
    return HistogramData(edges=edges, counts=counts)


@pytest.fixture
def gamma_unbinned(rng):
    """Generate gamma unbinned data (alpha=2, beta=0.5)."""
    values = rng.gamma(shape=2.0, scale=2.0, size=500)  # scale = 1/beta
    return UnbinnedData(values=values)


@pytest.fixture
def gamma_binned(rng):
    """Generate gamma binned data."""
    values = rng.gamma(shape=2.0, scale=2.0, size=500)
    edges = np.linspace(0, 15, 31)
    counts, _ = np.histogram(values, bins=edges)
    return HistogramData(edges=edges, counts=counts)


@pytest.fixture
def contaminated_data(rng):
    """Generate data with outliers."""
    normal_data = rng.normal(loc=5.0, scale=2.0, size=100)
    outliers = np.array([50.0, -50.0, 100.0])
    all_data = np.concatenate([normal_data, outliers])
    return UnbinnedData(values=all_data)
