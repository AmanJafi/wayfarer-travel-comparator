"""read train timetable and flight result pages, then normalize their listings."""

import math
import re
from datetime import date
from urllib.parse import urlencode

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

    # clean punctuation and check partial matches for familiar aliases
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

    # try to read the source's class fare table before building train cards
    classes = ["GN", "3E", "2S", "SL", "CC", "3A", "2A", "1A"]
    adult_match = re.search(r"Adult\s*(?:&#8377;|₹)\s*([\s\S]*?)<tr>", resp.text)
    fare_map: dict[str, float] = {}
    if adult_match:
        nums = [float(x) for x in re.findall(r"<td>(\d+)", adult_match.group(1))]
        fare_map = dict(zip(classes, nums))

    # these fallback amounts are estimates, not verified fares for this trip
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

        # convert the source's hour.minute display into total minutes
        dur_match = re.search(r"(\d+)\.(\d+)\s*hr", dur_text)
        if dur_match:
            dur_mins = int(dur_match.group(1)) * 60 + int(dur_match.group(2))
        else:
            dur_mins = 0

        # use the first two clock values in the row as departure and arrival
        row = span.find_parent("tr")
        row_text = row.get_text(" ") if row else ""
        times = re.findall(r"\b([0-2]?\d:[0-5]\d)\b", row_text)
        dep = times[0] if len(times) > 0 else None
        arr = times[1] if len(times) > 1 else None

        # pick the class estimate based on the train name when no route fare exists
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

    # without airport codes the flight search may not point to a real airport
    if not src.get("iata") and not dst.get("iata"):
        return [], f"no commercial airport configured for {origin} or {destination}"
    if not dst.get("iata") and dst["name"] == "Thrissur":
        return [], "no airport in Thrissur; nearest airport is Kochi (COK)"

    query_origin = src.get("iata") or src["name"]
    query_dest = dst.get("iata") or dst["name"]
    date_str = travel_date.strftime("%Y-%m-%d")

    query = f"flights from {query_origin} to {query_dest} on {date_str} oneway"
    url = "https://www.google.com/travel/flights?" + urlencode({
        "q": query,
        "hl": "en",
        "gl": "IN",
        "curr": "INR",
    })

    try:
        resp = httpx.get(url, headers=DEFAULT_HEADERS, timeout=12, follow_redirects=True)
        if resp.status_code != 200:
            return [], f"Google Flights returned HTTP {resp.status_code}"
    except httpx.TimeoutException:
        return [], "timed out contacting Google Flights"
    except Exception as e:
        return [], f"network error: {type(e).__name__}"

    soup = BeautifulSoup(resp.text, "html.parser")
    journeys: list[Journey] = []
    seen = set()

    # google exposes flight details in accessible labels; parse those as cards
    card_labels = (
        el.get("aria-label", "")
        for el in soup.find_all(attrs={"aria-label": True})
    )
    for card in card_labels:
        journey = _parse_google_flight_card(card, url)
        if not journey:
            continue
        airline = journey.provider
        dep_time = journey.departure_time
        fare = journey.price
        key = (airline, dep_time, fare)
        if key in seen:
            continue
        seen.add(key)
        journeys.append(journey)

    if journeys:
        return journeys, f"ok; {len(journeys)} live flights found via Google Flights"
    return [], f"no direct flights found for {src['name']} → {dst['name']} on {travel_date}"


def _parse_google_flight_card(label: str, source_url: str) -> Journey | None:
    # extract fare, airline, times, duration, and stops from one labeled flight card
    price_match = re.search(r"From\s+([\d,]+)\s+Indian rupees", label, re.I)
    if not price_match:
        price_match = re.search(r"(?:From\s+)?(?:₹|INR)\s*([\d,]+)", label, re.I)
    airline_match = re.search(r"with\s+([^.]+)\.", label, re.I)
    departure_match = re.search(
        r"(?:Leaves|Departs)\s+.*?at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)", label, re.I
    )
    arrival_match = re.search(
        r"arrives\s+.*?at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)", label, re.I
    )
    duration_match = re.search(
        r"Total duration\s+(\d+)\s*hr?\s*(\d+)?\s*m(?:in)?", label, re.I
    )
    stops_match = re.search(r"(Nonstop|Non-stop|\d+\s+stops?)", label, re.I)

    # skip incomplete labels rather than showing a partly guessed flight
    if not price_match or not duration_match or not airline_match:
        return None

    fare = float(price_match.group(1).replace(",", ""))
    duration = int(duration_match.group(1)) * 60 + int(duration_match.group(2) or 0)
    if fare <= 0 or duration <= 0:
        return None

    transfers = 0
    if stops_match and "non" not in stops_match.group(1).lower():
        count = re.search(r"\d+", stops_match.group(1))
        transfers = int(count.group()) if count else 1

    return Journey(
        mode="Flight",
        provider=airline_match.group(1).strip(),
        price=fare,
        duration_minutes=duration,
        transfers=transfers,
        departure_time=departure_match.group(1).strip() if departure_match else None,
        arrival_time=arrival_match.group(1).strip() if arrival_match else None,
        source_url=source_url,
    )


def scrape_flight_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    journeys, _ = scrape_flight_with_status(origin, destination, travel_date)
    return journeys


def scrape_all_options(origin: str, destination: str, travel_date: date) -> list[Journey]:
    res: list[Journey] = []
    res.extend(scrape_train_options(origin, destination, travel_date))
    res.extend(scrape_flight_options(origin, destination, travel_date))
    return res
