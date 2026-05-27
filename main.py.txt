from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

app = FastAPI(
    title="Vessel Schedule API (Free Scraping Version)",
    version="1.0.0"
)

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# CMA CGM SCRAPER
# -----------------------------

def scrape_cma(vessel_name=None, imo=None):
    """
    Scrapes CMA CGM vessel schedules using vessel name or IMO.
    Returns a list of port calls with ETA/ETD.
    """

    base_url = "https://www.cma-cgm.com/api/vessel/voyages?"
    params = {}

    if imo:
        params["imo"] = imo
    elif vessel_name:
        params["vesselName"] = vessel_name
    else:
        return None

    try:
        response = requests.get(base_url, params=params, timeout=15)
        if response.status_code != 200:
            return None
    except:
        return None

    data = response.json()

    if "voyages" not in data or len(data["voyages"]) == 0:
        return None

    vessel_info = data.get("vessel", {})
    vessel_name = vessel_info.get("name")
    imo = vessel_info.get("imo")

    calls = []
    for voyage in data["voyages"]:
        for call in voyage.get("calls", []):
            calls.append({
                "port_name": call.get("portName"),
                "port_code": call.get("portCode"),
                "eta": call.get("eta"),
                "etd": call.get("etd"),
                "voyage": voyage.get("voyageNumber"),
                "service": voyage.get("serviceName"),
                "carrier": "CMA CGM",
                "vessel_name": vessel_name,
                "imo": imo
            })

    return {
        "vessel_name": vessel_name,
        "imo": imo,
        "next_calls": calls
    }

# -----------------------------
# HEALTH CHECK
# -----------------------------

@app.get("/health")
def health():
    return {"status": "ok"}

# -----------------------------
# VESSEL SEARCH ENDPOINT
# -----------------------------

@app.get("/search/vessel")
def search_vessel(
    vessel_name: str | None = Query(default=None, description="Vessel name"),
    imo: str | None = Query(default=None, description="IMO number")
):
    # Try CMA CGM
    cma_result = scrape_cma(vessel_name, imo)
    if cma_result:
        return cma_result

    raise HTTPException(status_code=404, detail="No schedule found for this vessel.")
