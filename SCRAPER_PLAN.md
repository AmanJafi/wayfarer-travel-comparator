# scraper implementation plan

## current scope

The app compares train and flight options for a one-way trip. Bus scraping was removed because verified bus listings were not reliably available across different routes and dates; the app no longer presents a bus category or bus fares.

## current sources

| source | mode | implementation | limitation |
| --- | --- | --- | --- |
| eRail | train | reads public train listing pages and normalizes matching train details | some routes or dates may be unavailable or return no matching listings |
| Google Flights | flight | reads public Google Flights web results and normalizes flight details | pages may return no listings or change their markup |

## quality checks

- Require a valid provider, positive price, and positive duration before returning a listing.
- Return source status with results so an empty response is distinguishable from a successful search with no options.
- Keep each source independent so one failure does not suppress the other mode.
- Run backend tests from `backend/` with `./venv/bin/python -m unittest discover -s tests`.

The scrapers only use public website content. They do not bypass login or CAPTCHA protections and do not invent fares when a source cannot be verified.
