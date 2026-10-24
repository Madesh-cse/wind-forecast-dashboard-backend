
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.forecast_service import fetch_wind_forecasts


@pytest.mark.anyio
async def test_fetch_wind_forecasts_filters_january_delivery_periods():
    mock_response = httpx.Response(
        200,
        json=[
            {
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T10:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "generation": 12000,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-31T10:00:00Z",
                "startTime": "2026-02-01T00:00:00Z",
                "generation": 13000,
            },
        ],
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch(
        "app.services.forecast_service.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await fetch_wind_forecasts()

    assert len(results) == 1
    assert results[0]["startTime"] == "2026-01-01T00:00:00Z"
    assert results[0]["publishTime"] == "2025-12-31T10:00:00Z"
    assert results[0]["generation"] == 12000.0
