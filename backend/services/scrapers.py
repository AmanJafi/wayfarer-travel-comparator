import os
import re
from datetime import date
from string import Formatter
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from models import Journey


# these settings let each source be changed without changing python code
SCRAPER_SETTINGS = {
    "train": {
        "url": "TRAIN_SEARCH_URL",
        "card": "TRAIN_RESULT_SELECTOR",
        "provider": "TRAIN_PROVIDER_SELECTOR",
        "price": "TRAIN_PRICE_SELECTOR",
        "duration": "TRAIN_DURATION_SELECTOR",
        "transfers": "TRAIN_TRANSFERS_SELECTOR",
    },
    "flight": {
        "url": "FLIGHT_SEARCH_URL",
        "card": "FLIGHT_RESULT_SELECTOR",
        "provider": "FLIGHT_PROVIDER_SELECTOR",
        "price": "FLIGHT_PRICE_SELECTOR",
        "duration": "FLIGHT_DURATION_SELECTOR",
        "transfers": "FLIGHT_TRANSFERS_SELECTOR",
    },
}


def _build_search_url(template: str, origin: str, destination: str, travel_date: date) -> str:
    # replace search values inside the configured source url
    values = {
        "origin": quote_plus(origin),
        "destination": quote_plus(destination),
        "travel_date": travel_date.isoformat(),
    }
    fields = {field_name for _, field_name, _, _ in Formatter().parse(template) if field_name}
    return template.format(**{field: values.get(field, "") for field in fields})


def _read_number(value: str) -> float:
    # keep only digits and decimal separators from prices such as ₹1,299
    cleaned = "".join(character for character in value if character.isdigit() or character in ".,")
    cleaned = cleaned.replace(",", "")
    return float(cleaned) if cleaned else 0


def _read_duration(value: str) -> int:
    # convert common duration text such as 6h 30m into minutes
    text = value.lower().replace("hours", "h").replace("hour", "h")
    text = text.replace("minutes", "m").replace("minute", "m")
    hours = 0
    minutes = 0
    current = ""
    for character in text:
        if character.isdigit():
            current += character
        elif character == "h" and current:
            hours = int(current)
            current = ""
        elif character == "m" and current:
            minutes = int(current)
            current = ""
    return hours * 60 + minutes


def _read_transfers(value: str) -> int:
    # find the first number in text such as 1 transfer or non-stop
    digits = "".join(character for character in value if character.isdigit())
    if digits:
        return int(digits)
    # unknown transfer text also becomes zero in this simple helper
    return 0 if "non-stop" in value.lower() or "direct" in value.lower() else 0


def _text(card: BeautifulSoup, selector: str, default: str = "") -> str:
    # safely read text from one css-selected field inside a result card
    element = card.select_one(selector) if selector else None
    return element.get_text(" ", strip=True) if element else default


def _scrape_results(mode: str, origin: str, destination: str, travel_date: date) -> list[Journey]:
    # fetch and turn one configured html source into normalised journeys
    settings = SCRAPER_SETTINGS[mode]
    source_url = os.getenv(settings["url"])
    if not source_url:
        return []

    url = _build_search_url(source_url, origin, destination, travel_date)
    headers = {"User-Agent": os.getenv("SCRAPER_USER_AGENT", "TravelCompanion/1.0")}

    try:
        response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    # read only cards matching the selectors configured for this source
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select(os.getenv(settings["card"], "[data-journey]"))
    journeys = []
    for card in cards:
        provider = _text(card, os.getenv(settings["provider"], ""), mode.title())
        price = _read_number(_text(card, os.getenv(settings["price"], "")))
        duration = _read_duration(_text(card, os.getenv(settings["duration"], "")))
        transfers = _read_transfers(_text(card, os.getenv(settings["transfers"], "")))
        if price and duration:
            # only add a result when the two key numeric fields were parsed
            journeys.append(
                Journey(
                    mode=mode.title(),
                    provider=provider,
                    price=price,
                    duration_minutes=duration,
                    transfers=transfers,
                )
            )
    return journeys


def scrape_train_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    # scrape train results from the configured train source
    return _scrape_results("train", origin, destination, travel_date)


def scrape_flight_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    # scrape flight results from the configured flight source
    return _scrape_results("flight", origin, destination, travel_date)


def scrape_all_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    # run every mode scraper and keep working if one source is unavailable
    journeys = []
    for scraper in (scrape_train_options, scrape_flight_options):
        journeys.extend(scraper(origin, destination, travel_date))
    return journeys
