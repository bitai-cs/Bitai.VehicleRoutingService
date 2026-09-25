"""Rating thresholds from DASHBOARD_SPECIFICATION.md / the reference report.

Every rating carries a text label so status is never conveyed by colour alone.
"""

from __future__ import annotations

from enum import StrEnum


class Rating(StrEnum):
    GOOD = "good"
    WARNING = "warning"
    BAD = "bad"
    INFO = "info"

    @property
    def label(self) -> str:
        return {"good": "Good", "warning": "Warning", "bad": "Poor", "info": "Info"}[self.value]


def high_is_good(value: float, green_min: float, amber_min: float) -> Rating:
    if value >= green_min:
        return Rating.GOOD
    if value >= amber_min:
        return Rating.WARNING
    return Rating.BAD


def low_is_good(value: float, green_max: float, amber_max: float) -> Rating:
    if value <= green_max:
        return Rating.GOOD
    if value <= amber_max:
        return Rating.WARNING
    return Rating.BAD


def mid_band_is_good(value: float, green: tuple[float, float], amber: tuple[float, float]) -> Rating:
    if green[0] <= value <= green[1]:
        return Rating.GOOD
    if amber[0] <= value <= amber[1]:
        return Rating.WARNING
    return Rating.BAD


# Service level (semaphore in the executive summary): green >= 95, amber >= 85.
SERVICE_LEVEL_GREEN = 95.0
SERVICE_LEVEL_AMBER = 85.0
SERVICE_LEVEL_TARGET = 95.0
WEIGHTED_SERVICE_LEVEL_TARGET = 97.0

# Balance coefficients of variation: green <= 0.30, amber <= 0.50.
CV_GREEN_MAX = 0.30
CV_TARGET_MAX = 0.50

# Objective diagnostics alerts.
UNATTRIBUTED_RED_SHARE = 0.10
UNATTRIBUTED_GREEN_SHARE = 0.01
SOLVER_FAILURES_WARNING = 10_000

# Efficiency targets used in the summary table.
AVG_DISTANCE_PER_EMPLOYEE_MAX_KM = 20.0
AVG_TIME_PER_EMPLOYEE_MAX_MIN = 20.0
PRODUCTIVE_SHARE_MIN_PCT = 80.0
FLEET_UTILIZATION_BAND = (60.0, 90.0)
DEMAND_UTILIZATION_BAND = (60.0, 85.0)
P95_DEMAND_UTILIZATION_MAX = 100.0
AVG_STOP_WAIT_MAX_MIN = 5.0
P95_STOP_WAIT_MAX_MIN = 15.0


def service_level_rating(pct: float) -> Rating:
    return high_is_good(pct, SERVICE_LEVEL_GREEN, SERVICE_LEVEL_AMBER)


def cv_rating(value: float) -> Rating:
    return low_is_good(value, CV_GREEN_MAX, CV_TARGET_MAX)
