# Wind Forecast Accuracy Dashboard — Backend

A FastAPI backend for evaluating day-ahead UK wind generation forecast accuracy using actual generation and forecast data from the Elexon BMRS API.

**Live API:** https://wind-forecast-dashboard-backend.onrender.com  
**API Health:** https://wind-forecast-dashboard-backend.onrender.com/api/health  
**Frontend Dashboard:** https://wind-forecast-dashboard-frontend.vercel.app

## Overview

Wind generation forecasts help energy companies make day-ahead purchasing and operational decisions. Forecast errors can affect procurement costs, balancing requirements, and planning.

This backend retrieves historical wind generation actuals and forecasts, selects the latest eligible forecast for each delivery hour according to a configurable decision cutoff, and calculates forecast accuracy metrics.

The analysis covers **January 1–31, 2026**.

## Features

- Retrieve historical UK wind generation actuals from Elexon BMRS.
- Retrieve wind generation forecasts and their publication timestamps.
- Select the latest forecast published before the configured day-ahead decision cutoff.
- Aggregate valid half-hourly actuals into hourly values.
- Calculate Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and forecast bias.
- Report matched delivery periods and periods without eligible forecasts.
- Provide REST API endpoints for the frontend dashboard.
- Support Docker-based deployment and configurable CORS origins.

## Tech Stack

- **Python 3.12**
- **FastAPI** — REST API framework
- **Uvicorn** — ASGI server
- **HTTPX** — asynchronous HTTP requests
- **Pandas** — data processing
- **Pytest** — automated testing
- **Docker** — containerization
- **Elexon BMRS API** — UK electricity generation data

## Data Sources

Data is retrieved from the Elexon BMRS API:

- **FUELHH** — half-hourly generation data, filtered to wind.
- **WINDFOR** — wind generation forecasts, including delivery timestamps, publication timestamps, and forecast generation.

Official API documentation: https://bmrs.elexon.co.uk/api-documentation

The analysis uses delivery periods in January 2026 and retrieves forecast publications from the surrounding period so that forecasts issued before delivery can be evaluated.

## Forecast Evaluation Methodology

### 1. Actual generation

Actual wind generation records are filtered to the January 2026 analysis period. Valid hourly actuals are calculated from the expected half-hourly intervals.

An hourly actual is included only when the required intervals are present and valid. Duplicate or unexpected intervals are excluded rather than silently treated as complete data.

### 2. Day-ahead forecast selection

For each hourly delivery period:

1. Determine the configured decision cutoff on the preceding calendar day in the `Europe/London` timezone.
2. Find forecasts for the delivery period published at or before that cutoff.
3. Select the most recently published eligible forecast.
4. Match the selected forecast against the hourly actual generation.

The default cutoff is **12:00 Europe/London time**. This is a configurable implementation assumption because the assessment brief does not specify an exact decision time.

Timezone-aware timestamps are used to account for the UK daylight saving time rules.

### 3. Accuracy metrics

For each matched delivery period:

`Error = Forecast generation - Actual generation`

- **MAE:** Mean absolute difference between forecasts and actual generation.
- **RMSE:** Square root of the mean squared forecast error, which gives greater weight to larger errors.
- **Bias:** Mean signed forecast error. Positive bias indicates overforecasting; negative bias indicates underforecasting.

The API also reports the number of matched periods and periods without an eligible forecast.

Metrics are calculated over matched periods. Missing forecasts are reported separately rather than being treated as zero-generation forecasts.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API service information |
| GET | `/api/health` | Health check |
| GET | `/api/wind/actuals` | Retrieve actual wind generation data |
| GET | `/api/wind/analysis?cutoff=12:00` | Calculate forecast accuracy |

### Example requests

Health check:

```http
GET /api/health
```

Wind actuals:

```http
GET /api/wind/actuals
```

Forecast analysis:

```http
GET /api/wind/analysis?cutoff=12:00
```

The analysis endpoint returns the calculated accuracy metrics and the corresponding matched delivery-period results.

If an upstream data request fails, the API returns an HTTP 502 response with a user-facing error message.

## Getting Started

### Prerequisites

- Python 3.12 or compatible version
- Git
- pip

### 1. Clone the repository

```bash
git clone https://github.com/Madesh-cse/wind-forecast-dashboard-backend.git
cd wind-forecast-dashboard-backend
```

Replace the placeholder with your actual public GitHub repository URL.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure CORS

Set the `CORS_ORIGINS` environment variable to a comma-separated list of trusted frontend origins.

Example for local development:

```text
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

For production, include the deployed frontend origin:

```text
CORS_ORIGINS=https://wind-forecast-dashboard-frontend.vercel.app
```

Use your actual frontend URL if it differs. Do not commit secrets or local `.env` files.

### 5. Run the API

From the backend repository root:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs

## Docker

Build the backend image from the repository root:

```bash
docker build -t wind-forecast-dashboard-backend .
```

Run the container:

```bash
docker run --rm -p 8000:8000 \
  -e CORS_ORIGINS="http://localhost:5173,http://localhost:8080" \
  wind-forecast-dashboard-backend
```

On Windows PowerShell, use a single line or PowerShell backticks for line continuation.

## Running Tests

With the virtual environment activated, run:

```bash
python -m pytest -v
```

The test suite covers analysis calculations, incomplete actual periods, forecast selection, missing forecasts, timestamp and cutoff handling, API endpoints, and upstream failures.

## Project Structure

```text
wind-forecast-dashboard-backend/
├── app/
│   ├── main.py
│   └── services/
│       ├── elexon_service.py
│       ├── forecast_service.py
│       └── analysis_service.py
├── tests/
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── .gitignore
└── README.md
```

## Deployment

The backend is deployed on Render using Docker.

- **Production API:** https://wind-forecast-dashboard-backend.onrender.com
- **Health check:** https://wind-forecast-dashboard-backend.onrender.com/api/health

The frontend is hosted separately on Vercel and communicates with the backend through its public API endpoints.

## Limitations and Assumptions

- The evaluation period is January 2026.
- The default day-ahead decision cutoff is 12:00 Europe/London time and is configurable.
- Forecast availability and accuracy depend on the data returned by the upstream Elexon API.
- Only delivery periods with valid actuals and eligible forecasts contribute to the accuracy metrics.
- The analysis is retrospective and does not guarantee future forecast performance.
- The reported results depend on the selected cutoff and the forecast-selection methodology.

## AI Assistance Disclosure

AI tools were used to assist with development tasks, including implementation guidance, debugging, and documentation. The project code, evaluation logic, test results, and deployed behavior should be reviewed and validated by the project author.

## License

Add a license if you intend to distribute this project under specific reuse terms. No license is implied by this README alone.
