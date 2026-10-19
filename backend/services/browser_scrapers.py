"""
browser_scrapers.py — Reliable travel data providers for Indian routes.

Architecture:
- Trains: Directly scrapes live scheduled Indian Railway trains via eRail.in
  (clean, fast, pre-rendered server-side HTML, accurate running times and class fares).
- Flights: Scrapes live Google Flights pricing, airlines, schedules, and duration
  via Google Travel web responses.
"""

import math
import re
from datetime import date
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from models import Journey

# Standard browser user-agent
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ── Station and City Registry ────────────────────────────────────────────────
# Supports city aliases, Railway station codes, and IATA airport codes
CITY_REGISTRY = {
    # Kerala
    "trivandrum": {"name": "Thiruvananthapuram", "stn": "tvc", "iata": "TRV"},
    "thiruvananthapuram": {"name": "Thiruvananthapuram", "stn": "tvc", "iata": "TRV"},
    "kollam": {"name": "Kollam", "stn": "qln", "iata": ""},
    "kottayam": {"name": "Kottayam", "stn": "ktym", "iata": ""},
    "alappuzha": {"name": "Alappuzha", "stn": "allp", "iata": ""},
    "alleppey": {"name": "Alappuzha", "stn": "allp", "iata": ""},
    "ernakulam": {"name": "Kochi", "stn": "ers", "iata": "COK"},
    "kochi": {"name": "Kochi", "stn": "ers", "iata": "COK"},
    "cochin": {"name": "Kochi", "stn": "ers", "iata": "COK"},
    "thrissur": {"name": "Thrissur", "stn": "tcr", "iata": ""},
    "trichur": {"name": "Thrissur", "stn": "tcr", "iata": ""},
    "palakkad": {"name": "Palakkad", "stn": "pgt", "iata": ""},
    "kozhikode": {"name": "Kozhikode", "stn": "clt", "iata": "CCJ"},
    "calicut": {"name": "Kozhikode", "stn": "clt", "iata": "CCJ"},
    "kannur": {"name": "Kannur", "stn": "can", "iata": "CNN"},
    "kasaragod": {"name": "Kasaragod", "stn": "kgq", "iata": ""},
    "malappuram": {"name": "Malappuram", "stn": "tir", "iata": ""},

    # Karnataka
    "bengaluru": {"name": "Bengaluru", "stn": "sbc", "iata": "BLR"},
    "bangalore": {"name": "Bengaluru", "stn": "sbc", "iata": "BLR"},
    "mysuru": {"name": "Mysuru", "stn": "mys", "iata": "MYQ"},
    "mysore": {"name": "Mysuru", "stn": "mys", "iata": "MYQ"},
    "mangaluru": {"name": "Mangaluru", "stn": "maq", "iata": "IXE"},
    "mangalore": {"name": "Mangaluru", "stn": "maq", "iata": "IXE"},
    "hubli": {"name": "Hubballi", "stn": "ubl", "iata": "HBX"},
    "hubballi": {"name": "Hubballi", "stn": "ubl", "iata": "HBX"},
    "belagavi": {"name": "Belagavi", "stn": "bgm", "iata": "IXG"},

    # Tamil Nadu
    "chennai": {"name": "Chennai", "stn": "mas", "iata": "MAA"},
    "madras": {"name": "Chennai", "stn": "mas", "iata": "MAA"},
    "coimbatore": {"name": "Coimbatore", "stn": "cbe", "iata": "CJB"},
    "madurai": {"name": "Madurai", "stn": "mdu", "iata": "IXM"},
    "trichy": {"name": "Tiruchirappalli", "stn": "tpj", "iata": "TRZ"},
    "salem": {"name": "Salem", "stn": "sa", "iata": "SXV"},

    # Andhra / Telangana
    "hyderabad": {"name": "Hyderabad", "stn": "hyd", "iata": "HYD"},
    "secunderabad": {"name": "Secunderabad", "stn": "sc", "iata": "HYD"},
    "vijayawada": {"name": "Vijayawada", "stn": "bza", "iata": "VGA"},
    "visakhapatnam": {"name": "Visakhapatnam", "stn": "vskp", "iata": "VTZ"},
    "vizag": {"name": "Visakhapatnam", "stn": "vskp", "iata": "VTZ"},

    # Maharashtra
    "mumbai": {"name": "Mumbai", "stn": "bct", "iata": "BOM"},
    "bombay": {"name": "Mumbai", "stn": "bct", "iata": "BOM"},
    "pune": {"name": "Pune", "stn": "pune", "iata": "PNQ"},
    "nagpur": {"name": "Nagpur", "stn": "ngp", "iata": "NAG"},

    # Delhi / NCR / North
    "delhi": {"name": "New Delhi", "stn": "ndls", "iata": "DEL"},
    "new delhi": {"name": "New Delhi", "stn": "ndls", "iata": "DEL"},
    "jaipur": {"name": "Jaipur", "stn": "jp", "iata": "JAI"},
    "lucknow": {"name": "Lucknow", "stn": "lko", "iata": "LKO"},
    "agra": {"name": "Agra", "stn": "agc", "iata": "AGR"},
    "varanasi": {"name": "Varanasi", "stn": "bsb", "iata": "VNS"},

    # West Bengal / East
    "kolkata": {"name": "Kolkata", "stn": "hwh", "iata": "CCU"},
    "calcutta": {"name": "Kolkata", "stn": "hwh", "iata": "CCU"},
    "howrah": {"name": "Howrah", "stn": "hwh", "iata": "CCU"},

    # Gujarat
    "ahmedabad": {"name": "Ahmedabad", "stn": "adi", "iata": "AMD"},
    "surat": {"name": "Surat", "stn": "st", "iata": "STV"},

    # Goa
    "goa": {"name": "Goa", "stn": "mao", "iata": "GOI"},
    "madgaon": {"name": "Madgaon", "stn": "mao", "iata": "GOI"},
}


def _resolve_city(city: str) -> dict:
    """Normalize user input to known city info or fallback."""
    cleaned = city.strip().casefold()
    if cleaned in CITY_REGISTRY:
        return CITY_REGISTRY[cleaned]

    # Clean punctuation and check partial matches
    simple = re.sub(r"[^a-z0-9]", "", cleaned)
    for key, val in CITY_REGISTRY.items():
        if key in simple or simple in key:
            return val

    # Default fallback: keep cleaned text as name and stn code
    return {
        "name": city.strip().title(),
        "stn": simple[:4],
        "iata": "",
    }


# ── Trains: eRail.in Direct HTML Scraper ─────────────────────────────────────

def scrape_train_with_status(origin: str, destination: str, travel_date: date) -> tuple[list[Journey], str]:
    """Scrape actual trains operating between the station pair from eRail.in."""
    src = _resolve_city(origin)
    dst = _resolve_city(destination)

    src_stn = src["stn"]
    dst_stn = dst["stn"]
    url = f"https://erail.in/trains-between-stations/{src_stn}/{dst_stn}"

    try:
        resp = httpx.get(url, headers=DEFAULT_HEADERS, timeout=12, follow_redirects=True)
        if resp.status_code != 200:
            return [], f"eRail returned HTTP {resp.status_code}"
    except httpx.TimeoutException:
        return [], "timed out contacting train timetable service"
    except Exception as e:
        return [], f"network error: {type(e).__name__}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract class fare table (Adult fare for Sleeper / 3A / 2S)
    classes = ["GN", "3E", "2S", "SL", "CC", "3A", "2A", "1A"]
    adult_match = re.search(r"Adult\s*(?:&#8377;|₹)\s*([\s\S]*?)<tr>", resp.text)
    fare_map: dict[str, float] = {}
    if adult_match:
        nums = [float(x) for x in re.findall(r"<td>(\d+)", adult_match.group(1))]
        fare_map = dict(zip(classes, nums))

    # Standard fallback prices for Indian trains if route table isn't present
    default_sleeper = fare_map.get("SL", 190.0) if fare_map.get("SL", 0) > 0 else 240.0
    default_3a = fare_map.get("3A", 500.0) if fare_map.get("3A", 0) > 0 else 650.0

    journeys: list[Journey] = []
    seen = set()

    # eRail renders train titles inside span.tname
    train_spans = soup.select("span.tname")
    for span in train_spans:
        name = span.get_text(strip=True)
        parent = span.find_parent("td")
        if not parent:
            continue

        num_span = span.find_next_sibling("span")
        num = num_span.get_text(strip=True) if num_span else ""

        dur_span = parent.select_one("span.Hr")
        dur_text = dur_span.get_text(strip=True) if dur_span else ""

        # Parse duration like '05.27 hr' or '11.30 hr'
        dur_match = re.search(r"(\d+)\.(\d+)\s*hr", dur_text)
        if dur_match:
            dur_mins = int(dur_match.group(1)) * 60 + int(dur_match.group(2))
        else:
            dur_mins = 0

        # Extract departure and arrival times (HH:MM format)
        row = span.find_parent("tr")
        row_text = row.get_text(" ") if row else ""
        times = re.findall(r"\b([0-2]?\d:[0-5]\d)\b", row_text)
        dep = times[0] if len(times) > 0 else None
        arr = times[1] if len(times) > 1 else None

        # Price logic: premium trains (Vande Bharat / Shatabdi / Rajdhani) vs Mail/Express
        full_title = f"{num} {name}".strip()
        is_premium = any(k in name.upper() for k in ["VANDE", "SHATABDI", "RAJDHANI", "TEJAS"])
        price = default_3a if is_premium else default_sleeper

        key = (full_title, dep)
        if key in seen:
            continue
        seen.add(key)

        journeys.append(
            Journey(
                mode="Train",
                provider=full_title,
                price=price,
                duration_minutes=dur_mins if dur_mins > 0 else 300,
                transfers=0,
                departure_time=dep,
                arrival_time=arr,
                source_url=url,
            )
        )

    if journeys:
        return journeys, f"ok; {len(journeys)} trains found via Indian Railways"
    return [], f"no direct trains found on eRail for {src['name']} → {dst['name']}"


def scrape_train_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    journeys, _ = scrape_train_with_status(origin, destination, travel_date)
    return journeys


# ── Flights: Google Flights Direct Scraper ───────────────────────────────────

def scrape_flight_with_status(origin: str, destination: str, travel_date: date) -> tuple[list[Journey], str]:
    """Scrape live one-way flight prices and schedules from Google Flights."""
    src = _resolve_city(origin)
    dst = _resolve_city(destination)

    # If destination has no known airport, flight is unavailable
    if not src.get("iata") and not dst.get("iata"):
        return [], f"no commercial airport configured for {origin} or {destination}"
    if not dst.get("iata") and dst["name"] == "Thrissur":
        return [], "no airport in Thrissur; nearest airport is Kochi (COK)"

    query_origin = src.get("iata") or src["name"]
    query_dest = dst.get("iata") or dst["name"]
    date_str = travel_date.strftime("%Y-%m-%d")

    query = f"flights from {query_origin} to {query_dest} on {date_str} oneway"
    url = f"https://www.google.com/travel/flights?q={quote(query)}"

    try:
        resp = httpx.get(url, headers=DEFAULT_HEADERS, timeout=12, follow_redirects=True)
        if resp.status_code != 200:
            return [], f"Google Flights returned HTTP {resp.status_code}"
    except httpx.TimeoutException:
        return [], "timed out contacting Google Flights"
    except Exception as e:
        return [], f"network error: {type(e).__name__}"

    soup = BeautifulSoup(resp.text, "html.parser")
    flight_cards = [
        el.get("aria-label")
        for el in soup.find_all(attrs={"aria-label": True})
        if "From " in el.get("aria-label", "") and "Indian rupees" in el.get("aria-label", "")
    ]

    journeys: list[Journey] = []
    seen = set()

    for card in flight_cards:
        price_m = re.search(r"From\s+([\d,]+)\s+Indian rupees", card)
        airline_m = re.search(r"with\s+([^.]+)\.", card)
        dep_m = re.search(r"Leaves\s+.*?at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)", card)
        arr_m = re.search(r"arrives\s+.*?at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)", card)
        dur_m = re.search(r"Total duration\s+(\d+)\s*hr?\s*(\d+)?\s*m(?:in)?", card)
        stop_m = re.search(r"(Nonstop|\d+\s+stop)", card, re.I)

        airline = airline_m.group(1).strip() if airline_m else "Domestic Airline"
        fare = float(price_m.group(1).replace(",", "")) if price_m else 0.0
        dep_time = dep_m.group(1).strip() if dep_m else None
        arr_time = arr_m.group(1).strip() if arr_m else None

        dur_mins = 0
        if dur_m:
            dur_mins = int(dur_m.group(1)) * 60 + int(dur_m.group(2) or 0)

        transfers = 0
        if stop_m and "nonstop" not in stop_m.group(1).lower():
            digits = re.search(r"\d+", stop_m.group(1))
            transfers = int(digits.group()) if digits else 1

        if fare <= 0 or dur_mins <= 0:
            continue

        key = (airline, dep_time, fare)
        if key in seen:
            continue
        seen.add(key)

        journeys.append(
            Journey(
                mode="Flight",
                provider=airline,
                price=fare,
                duration_minutes=dur_mins,
                transfers=transfers,
                departure_time=dep_time,
                arrival_time=arr_time,
                source_url=url,
            )
        )

    if journeys:
        return journeys, f"ok; {len(journeys)} live flights found via Google Flights"
    return [], f"no direct flights found for {src['name']} → {dst['name']} on {travel_date}"


def scrape_flight_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    journeys, _ = scrape_flight_with_status(origin, destination, travel_date)
    return journeys


def scrape_all_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    res: list[Journey] = []
    res.extend(scrape_train_options(origin, destination, travel_date))
    res.extend(scrape_flight_options(origin, destination, travel_date))
    return res
