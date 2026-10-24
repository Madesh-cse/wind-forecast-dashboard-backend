
from datetime import datetime
from math import isclose

from app.services.analysis_service import (
    aggregate_actuals_hourly,
    evaluate_forecast_accuracy,
    get_decision_cutoff,
)


def make_actuals():
    """Two half-hour readings for each of two complete hours."""
    return [
        {"startTime": "2026-01-01T00:00:00Z", "generation": 100},
        {"startTime": "2026-01-01T00:30:00Z", "generation": 120},
        {"startTime": "2026-01-01T01:00:00Z", "generation": 200},
        {"startTime": "2026-01-01T01:30:00Z", "generation": 220},
    ]


def test_actuals_are_aggregated_to_hourly_averages():
    actuals = make_actuals()

    result = aggregate_actuals_hourly(actuals)

    assert len(result) == 2
    assert result[datetime.fromisoformat("2026-01-01T00:00:00+00:00")] == 110
    assert result[datetime.fromisoformat("2026-01-01T01:00:00+00:00")] == 210


def test_incomplete_actual_hour_is_excluded():
    actuals = make_actuals()
    actuals.append(
        {"startTime": "2026-01-01T02:00:00Z", "generation": 300}
    )

    result = aggregate_actuals_hourly(actuals)

    assert len(result) == 2
    assert datetime.fromisoformat("2026-01-01T02:00:00+00:00") not in result


def test_latest_forecast_before_cutoff_is_selected_and_metrics_are_correct():
    forecasts = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2025-12-31T10:00:00Z",
            "generation": 90,
        },
        {
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2025-12-31T11:30:00Z",
            "generation": 100,
        },
        {
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2025-12-31T12:01:00Z",
            "generation": 999,
        },
        {
            "startTime": "2026-01-01T01:00:00Z",
            "publishTime": "2025-12-31T11:00:00Z",
            "generation": 215,
        },
        {
            "startTime": "2026-01-01T01:00:00Z",
            "publishTime": "2025-12-31T11:30:00Z",
            "generation": 230,
        },
    ]

    result = evaluate_forecast_accuracy(make_actuals(), forecasts)

    assert result["matchedCount"] == 2
    assert result["missingForecastCount"] == 0

    # Actuals: 110, 210. Selected forecasts: 100, 230.
    assert [row["forecastGeneration"] for row in result["data"]] == [100, 230]
    assert [row["error"] for row in result["data"]] == [-10, 20]

    assert isclose(result["mae"], 15)
    assert isclose(result["rmse"], (250) ** 0.5)
    assert isclose(result["bias"], 5)

    assert all(
        row["publishTime"] != "2025-12-31T12:01:00+00:00"
        for row in result["data"]
    )


def test_missing_forecast_is_counted_not_treated_as_zero():
    actuals = make_actuals()
    forecasts = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2025-12-31T11:30:00Z",
            "generation": 100,
        }
    ]

    result = evaluate_forecast_accuracy(actuals, forecasts)

    assert result["matchedCount"] == 1
    assert result["missingForecastCount"] == 1
    assert result["mae"] == 10
    assert result["bias"] == -10


def test_daylight_saving_cutoff_uses_london_timezone():
    delivery_time = datetime.fromisoformat("2026-07-01T00:00:00+00:00")

    cutoff = get_decision_cutoff(delivery_time, "12:00")

    # London is on BST (UTC+1) on 30 June 2026.
    assert cutoff.isoformat() == "2026-06-30T12:00:00+01:00"
    assert cutoff.astimezone().utcoffset() is not None
    assert cutoff.utcoffset().total_seconds() == 3600


def test_no_eligible_forecasts_returns_no_metrics():
    forecasts = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2025-12-31T12:01:00Z",
            "generation": 100,
        }
    ]

    result = evaluate_forecast_accuracy(make_actuals(), forecasts)

    assert result["matchedCount"] == 0
    assert result["missingForecastCount"] == 2
    assert result["mae"] is None
    assert result["rmse"] is None
    assert result["bias"] is None
    assert result["data"] == []
