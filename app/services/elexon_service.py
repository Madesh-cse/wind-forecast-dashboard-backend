
import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
START_DATE = "2026-01-01"
END_DATE = "2026-01-31"


async def fetch_wind_actuals() -> list[dict]:
    """Fetch January 2026 half-hourly wind generation actuals."""

    url = f"{BASE_URL}/datasets/FUELHH/stream"

    params = {
        "settlementDateFrom": START_DATE,
        "settlementDateTo": END_DATE,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("data", [])
    else:
        raise ValueError("Unexpected response format from Elexon")

    results = []

    for record in records:
        if record.get("fuelType") != "WIND":
            continue

        start_time = record.get("startTime")
        generation = record.get("generation")

        if not start_time or generation is None:
            continue

        if not start_time.startswith("2026-01-"):
            continue

        results.append({
            "startTime": start_time,
            "settlementDate": record.get("settlementDate"),
            "settlementPeriod": record.get("settlementPeriod"),
            "fuelType": "WIND",
            "generation": float(generation),
        })

    results.sort(key=lambda item: item["startTime"])

    return results
