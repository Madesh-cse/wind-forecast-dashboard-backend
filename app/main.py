
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.services.elexon_service import fetch_wind_actuals
from app.services.analysis_service import evaluate_forecast_accuracy
from app.services.forecast_service import fetch_wind_forecasts

app = FastAPI(
    title="Wind Forecast Accuracy API",
    description="API for UK wind generation forecasts and actuals.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8080,https://wind-forecast-dashboard-frontend.vercel.app",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Wind Forecast Accuracy API is running"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "wind-forecast-api",
    }


@app.get("/api/wind/actuals")
async def get_wind_actuals():
    try:
        records = await fetch_wind_actuals()

        return {
            "dataset": "FUELHH",
            "fuelType": "WIND",
            "period": {
                "from": "2026-01-01",
                "to": "2026-01-31",
            },
            "count": len(records),
            "data": records,
        }

    except Exception as exc:
        # Log the error server-side without exposing internals to clients.
        print(f"Failed to fetch Elexon wind actuals: {exc}")

        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve wind generation data from Elexon.",
        ) from exc


@app.get("/api/wind/analysis")
async def get_wind_analysis(cutoff: str = "12:00"):
    try:
        actuals, forecasts = await asyncio.gather(
            fetch_wind_actuals(),
            fetch_wind_forecasts(),
        )

        return evaluate_forecast_accuracy(
            actuals=actuals,
            forecasts=forecasts,
            cutoff=cutoff,
        )
    except Exception as exc:
        print(f"Wind analysis failed: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Unable to calculate wind forecast accuracy.",
        ) from exc