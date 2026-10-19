from datetime import date
import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import Journey
from services.comparator import sort_by_duration, sort_by_price, sort_by_transfers
from services.browser_scrapers import (
    scrape_train_with_status,
    scrape_flight_with_status,
)


app = FastAPI(title="Travel Comparator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: date
    sort_by: Literal["price", "duration", "transfers"] = "price"


@app.get("/")
@app.get("/api")
@app.get("/api/")
def home():
    return {"message": "Travel Comparator API is running"}


@app.post("/search")
@app.post("/api/search")
def search(request: SearchRequest):
    # Run the available train and flight scrapers
    train_journeys, train_status = scrape_train_with_status(
        request.origin, request.destination, request.travel_date
    )
    flight_journeys, flight_status = scrape_flight_with_status(
        request.origin, request.destination, request.travel_date
    )

    all_journeys: list[Journey] = train_journeys + flight_journeys

    if request.sort_by == "price":
        all_journeys = sort_by_price(all_journeys)
    elif request.sort_by == "duration":
        all_journeys = sort_by_duration(all_journeys)
    else:
        all_journeys = sort_by_transfers(all_journeys)

    return {
        "origin": request.origin,
        "destination": request.destination,
        "travel_date": request.travel_date,
        "journeys": all_journeys,
        "live_results": bool(all_journeys),
        "sources": [
            {"name": "Indian Railways (eRail)", "status": train_status},
            {"name": "Google Flights", "status": flight_status},
        ],
        "message": f"Found {len(all_journeys)} total travel options.",
    }
