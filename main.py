from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from datetime import date, timedelta

# Load Traqo API key from environment variable
TRAQO_API_KEY = os.getenv("TRAQO_API_KEY")
TRAQO_BASE_URL = "https://api.traqo.com/ocean"

app = FastAPI(
    title="Vessel Schedule API",
    version="1.0.0"
)

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def traqo_get(path: str, params: dict):
    """Helper function to call Traqo API."""
    headers = {"Authorization": f"Bearer {TRAQO_API_KEY}"}
    url = f"{TRAQO_BASE_URL}{path}"
    response = requests.get(url, headers=headers, params=params, timeout=15)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Error from Traqo API")

    return response.json()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search/port-to-port")
def search_port_to_port(
    origin: str = Query(..., description="Origin port code (e.g. CNYTN)"),
    destination: str = Query(..., description="Destination port code (e.g. NLRTM)"),
    date_from: date = Query(default=date.today()),
    date_to: date = Query(default=date.today() + timedelta(days=14))
):
    params = {
        "origin": origin,
        "destination": destination,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
    }

    data = traqo_get("/schedules", params)

    results = []
    for item in data.get("schedules", []):
        results.append({
            "carrier": item.get("carrier"),
            "service": item.get("service"),
            "vessel_name": item.get("vessel_name"),
            "imo": item.get("imo"),
            "voyage": item.get("voyage"),
            "etd": item.get("etd"),
            "eta": item.get("eta"),
            "origin": item.get("origin"),
            "destination": item.get("destination"),
            "transit_time_days": item.get("transit_time_days"),
        })

    return {"results": results}

@app.get("/search/vessel")
def search_vessel(
    vessel_name: str | None = Query(default=None, description="Vessel name"),
    imo: str | None = Query(default=None, description="IMO number"),
    days_ahead: int = Query(default=30, ge=1, le=90)
):
    if not vessel_name and not imo:
        raise HTTPException(status_code=400, detail="Provide vessel_name or imo")

    date_from = date.today()
    date_to = date_from + timedelta(days=days_ahead)

    params = {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
    }

    if vessel_name:
        params["vessel_name"] = vessel_name
    if imo:
        params["imo"] = imo

    data = traqo_get("/vessel-schedules", params)

    calls = []
    for call in data.get("calls", []):
        calls.append({
            "vessel_name": call.get("vessel_name"),
            "imo": call.get("imo"),
            "voyage": call.get("voyage"),
            "port_name": call.get("port_name"),
            "port_code": call.get("port_code"),
            "eta": call.get("eta"),
            "etd": call.get("etd"),
            "carrier": call.get("carrier"),
        })

    return {
        "vessel_name": vessel_name or data.get("vessel_name"),
        "imo": imo or data.get("imo"),
        "next_calls": calls
    }
