import httpx
from collections import Counter
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

# Include December publication times because forecasts published in
# December may apply to January delivery periods.
PUBLISH_FROM = "2025-12-01T00:00:00Z"
PUBLISH_TO = "2026-02-01T00:00:00Z"

START_DATE = "2026-01-01"
END_DATE = "2026-02-01"


async def fetch_wind_forecasts() -> list[dict]:
    """Fetch forecasts published around January 2026."""
    url = f"{BASE_URL}/datasets/WINDFOR/stream"

    params = {
        "publishDateTimeFrom": PUBLISH_FROM,
        "publishDateTimeTo": PUBLISH_TO,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, list):
        raise ValueError("Unexpected response format from Elexon")

    results = []

    for record in payload:
        start_time = record.get("startTime")
        publish_time = record.get("publishTime")
        generation = record.get("generation")

        if not start_time or not publish_time or generation is None:
            continue

        if not START_DATE <= start_time[:10] < END_DATE:
            continue

        results.append(
            {
                "startTime": start_time,
                "publishTime": publish_time,
                "generation": float(generation),
            }
        )

    results.sort(key=lambda row: (row["startTime"], row["publishTime"]))

    print("\n--- WINDFOR delivery timestamps ---")


    for row in results[:12]:
      print(
        "startTime:",
        row["startTime"],
        "| publishTime:",
        row["publishTime"],
        "| generation:",
        row["generation"],
     )

    print("\n--- Forecasts around midnight ---")

    for row in results:
      if row["startTime"].startswith("2026-01-01T"):
        print(row)

        # Show only the first 10 records for this date.
        if row["startTime"].startswith("2026-01-01T05:"):
            break
        
    delivery_counts = Counter(
    row["startTime"][:10] for row in results
    )

    print("\n--- Forecast records by delivery date ---")
    for day in sorted(delivery_counts)[:5]:
      print(day, delivery_counts[day])

    print("Total forecast candidates:", len(results))
    print(
    "Distinct delivery timestamps:",
    len({row["startTime"] for row in results}),
    )

    return results
