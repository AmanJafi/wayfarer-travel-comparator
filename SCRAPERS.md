# travelcompanion scrapers

The `/search` endpoint in `backend/main.py` collects train and flight options and returns source status alongside the journeys. Bus scraping has been removed because it only produced dependable results for a narrow set of routes and dates.

## trains and flights

- `scrape_train_with_status` in `backend/services/browser_scrapers.py` reads train listings from eRail.
- `scrape_flight_with_status` in `backend/services/browser_scrapers.py` reads flight listings from Google Flights.
- The optional generic scraper helpers in `backend/services/scrapers.py` can be configured for train or flight HTML with the matching environment variables in `SCRAPER_SETTINGS`.
- Each successful listing is normalized into a journey with its mode, provider, price, duration, and available times/source link. Unavailable or empty sources report a status instead of inventing fares.

## checks

Run backend checks from `backend/` with `./venv/bin/python -m unittest discover -s tests`.

The scrapers use public website pages. They do not call a provider API, bypass a login or CAPTCHA, or fabricate fares when a source cannot be verified.
