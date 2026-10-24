
from collections import defaultdict
from datetime import datetime, time, timedelta
from math import sqrt
from statistics import mean
from zoneinfo import ZoneInfo


DECISION_TIMEZONE = "Europe/London"
DAY_AHEAD_CUTOFF = "12:00"
UTC = ZoneInfo("UTC")


def parse_datetime(value: str) -> datetime:
    """Parse an ISO timestamp and require timezone information."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value}")

    return parsed


def get_decision_cutoff(
    delivery_time: datetime,
    cutoff: str = DAY_AHEAD_CUTOFF,
) -> datetime:
    """
    Return the configured cutoff on the London calendar day
    before the delivery date.
    """
    timezone = ZoneInfo(DECISION_TIMEZONE)
    local_delivery = delivery_time.astimezone(timezone)
    previous_day = local_delivery.date() - timedelta(days=1)

    try:
        hour, minute = map(int, cutoff.split(":"))
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid cutoff time: {cutoff}") from None

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid cutoff time: {cutoff}")

    return datetime.combine(
        previous_day,
        time(hour=hour, minute=minute),
        tzinfo=timezone,
    )


def aggregate_actuals_hourly(
    actuals: list[dict],
) -> dict[datetime, float]:
    """
    Aggregate half-hourly actual generation into hourly averages.

    An hour is included only if it has exactly one valid reading
    at HH:00 and one at HH:30 UTC.

    Duplicate timestamps or malformed interval timestamps invalidate
    that hour. Missing or null readings are skipped, so an incomplete
    hour is excluded rather than treated as zero.
    """
    hourly_values: dict[datetime, dict[datetime, float]] = defaultdict(dict)
    invalid_hours: set[datetime] = set()

    for row in actuals:
        if not row.get("startTime") or row.get("generation") is None:
            continue

        timestamp = parse_datetime(row["startTime"]).astimezone(UTC)

        hour_start = timestamp.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        # Only accept exact hourly and half-hourly boundaries.
        if (
            timestamp.second != 0
            or timestamp.microsecond != 0
            or timestamp.minute not in (0, 30)
        ):
            invalid_hours.add(hour_start)
            continue

        # A duplicate interval must not silently distort the average.
        if timestamp in hourly_values[hour_start]:
            invalid_hours.add(hour_start)
            continue

        try:
            generation = float(row["generation"])
        except (TypeError, ValueError):
            invalid_hours.add(hour_start)
            continue

        hourly_values[hour_start][timestamp] = generation

    hourly_actuals: dict[datetime, float] = {}

    for hour_start, readings in hourly_values.items():
        if hour_start in invalid_hours:
            continue

        if len(readings) != 2:
            continue

        interval_minutes = {
            timestamp.minute for timestamp in readings
        }

        if interval_minutes != {0, 30}:
            continue

        hourly_actuals[hour_start] = mean(readings.values())

    return hourly_actuals


def evaluate_forecast_accuracy(
    actuals: list[dict],
    forecasts: list[dict],
    cutoff: str = DAY_AHEAD_CUTOFF,
) -> dict:
    """
    Compare hourly wind forecasts with hourly actual averages.

    For each actual delivery hour:
    1. Determine the configured cutoff on the previous London day.
    2. Keep forecasts published on or before that cutoff.
    3. Select the latest eligible publication.
    4. Compare it with the actual for the same delivery timestamp.

    Error convention:
        error = forecast generation - actual generation

    Positive bias therefore means overforecasting.
    """
    actual_by_time = aggregate_actuals_hourly(actuals)

    forecasts_by_time: dict[datetime, list[dict]] = defaultdict(list)

    for row in forecasts:
        if (
            not row.get("startTime")
            or not row.get("publishTime")
            or row.get("generation") is None
        ):
            continue

        delivery_time = parse_datetime(row["startTime"]).astimezone(UTC)
        publish_time = parse_datetime(row["publishTime"])

        try:
            generation = float(row["generation"])
        except (TypeError, ValueError):
            continue

        forecasts_by_time[delivery_time].append(
            {
                "publishTime": publish_time,
                "generation": generation,
            }
        )

    matched = []
    missing_forecasts = 0

    for delivery_time, actual_generation in sorted(
        actual_by_time.items()
    ):
        decision_cutoff = get_decision_cutoff(delivery_time, cutoff)

        eligible = [
            forecast
            for forecast in forecasts_by_time.get(delivery_time, [])
            if forecast["publishTime"] <= decision_cutoff
        ]

        if not eligible:
            missing_forecasts += 1
            continue

        # Choose the most recent forecast available by the cutoff.
        selected = max(
            eligible,
            key=lambda forecast: forecast["publishTime"],
        )

        forecast_generation = selected["generation"]
        error = forecast_generation - actual_generation

        matched.append(
            {
                "startTime": delivery_time.isoformat(),
                "publishTime": selected["publishTime"].isoformat(),
                "actualGeneration": actual_generation,
                "forecastGeneration": forecast_generation,
                "error": error,
                "absoluteError": abs(error),
            }
        )

    print("Actual half-hourly records:", len(actuals))
    print("Complete hourly actual periods:", len(actual_by_time))
    print("Matched hourly forecast periods:", len(matched))
    print("Hourly periods missing eligible forecasts:", missing_forecasts)
    print("Forecast records fetched:", len(forecasts))

    if not matched:
        return {
            "cutoff": cutoff,
            "timezone": DECISION_TIMEZONE,
            "matchedCount": 0,
            "missingForecastCount": missing_forecasts,
            "mae": None,
            "rmse": None,
            "bias": None,
            "data": [],
        }

    errors = [row["error"] for row in matched]

    mae = mean(abs(error) for error in errors)
    rmse = sqrt(mean(error**2 for error in errors))
    bias = mean(errors)

    return {
        "cutoff": cutoff,
        "timezone": DECISION_TIMEZONE,
        "matchedCount": len(matched),
        "missingForecastCount": missing_forecasts,
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "data": matched,
    }
