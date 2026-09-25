"""Small statistics helpers, ported from the reference ``sample/solver/reporting.py``.

Semantics are kept identical so numbers match the reference reports: linear
interpolation percentiles, *population* standard deviation, and a coefficient
of variation that is 0 when the mean is 0.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: Sequence[float], fraction: float) -> float:
    """Percentile with linear interpolation; ``fraction`` in [0, 1]."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * fraction
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def population_std(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    centre = mean(values)
    return sqrt(sum((v - centre) ** 2 for v in values) / len(values))


def coefficient_of_variation(values: Sequence[float]) -> float:
    centre = mean(values)
    if centre == 0:
        return 0.0
    return population_std(values) / centre
