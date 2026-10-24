
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Wind Forecast Accuracy API is running"
    }


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "wind-forecast-api",
    }


@patch(
    "app.main.fetch_wind_actuals",
    new_callable=AsyncMock,
)
def test_wind_actuals_endpoint(mock_fetch):
    mock_fetch.return_value = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 12500.0,
        }
    ]

    response = client.get("/api/wind/actuals")

    assert response.status_code == 200

    payload = response.json()

    assert payload["dataset"] == "FUELHH"
    assert payload["fuelType"] == "WIND"
    assert payload["count"] == 1
    assert payload["period"]["from"] == "2026-01-01"
    assert payload["period"]["to"] == "2026-01-31"

    assert payload["data"][0]["generation"] == 12500.0
    assert payload["data"][0]["fuelType"] == "WIND"

    mock_fetch.assert_awaited_once()


@patch(
    "app.main.fetch_wind_actuals",
    new_callable=AsyncMock,
)
def test_wind_actuals_upstream_failure(mock_fetch):
    mock_fetch.side_effect = RuntimeError("Upstream service unavailable")

    response = client.get("/api/wind/actuals")

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Unable to retrieve wind generation data from Elexon."
    }
