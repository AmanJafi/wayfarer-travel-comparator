# Wayfarer — travel comparison

Wayfarer compares train and flight options for a route and travel date. It collects publicly visible listings, normalizes each result, and lets you sort by price, duration, or transfers. Bus fares are not currently supported.

## What it does

- Searches public eRail train listings and Google Flights results.
- Shows provider, fare, duration, departure/arrival times when available, and the source page.
- Groups results by travel mode and summarizes the lowest fare and quickest trip.
- Keeps source status with each search so unavailable sources are visible rather than replaced with made-up fares.

There is no stored dataset or machine-learning model. Listings are fetched when a search is submitted. The backend normalizes them into the `Journey` model and sorts them using simple price, duration, and transfer comparisons.

## Project layout

```text
backend/
  main.py                    FastAPI search endpoint
  models.py                  normalized journey schema
  services/browser_scrapers.py  train and flight website scrapers
  services/comparator.py     result sorting
  tests/                     backend tests
frontend/
  src/                       React + TypeScript interface
  package.json               frontend scripts and dependencies
SCRAPERS.md                  scraper behavior and limitations
SCRAPER_PLAN.md              current source scope and quality checks
```

## Run locally

### backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`; its health check is `/` and search endpoint is `POST /search`.

### frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173`). The frontend defaults to the local backend. To use another backend, create `frontend/.env.local` with:

```dotenv
VITE_API_BASE_URL=https://your-backend.example.com
```

## tests and build

```bash
cd backend
python -m unittest discover -s tests

cd ../frontend
npm ci
npm run build
```

## deploy on Vercel

Deploy the frontend and backend as two Vercel projects connected to the same GitHub repository:

1. Create the backend project and set its **Root Directory** to `backend`. Vercel detects the FastAPI app in `main.py` and installs `backend/requirements.txt`.
2. After its first deployment, copy the backend's public HTTPS URL.
3. Create the frontend project from the same repository and set its **Root Directory** to `frontend`. Use the Vite defaults: build command `npm run build`, output directory `dist`.
4. In the frontend project's environment variables, set `VITE_API_BASE_URL` to the backend HTTPS origin (no trailing slash), then redeploy the frontend.
5. In the backend project's environment variables, set `FRONTEND_ORIGINS` to the frontend's exact origin, such as `https://your-app.vercel.app`. Add any other approved frontend origins as a comma-separated list.

Redeploy after changing project environment variables. For Vercel preview domains, add their frontend origin to the backend's `FRONTEND_ORIGINS` value when needed.

## data and limitations

This project reads public website pages, not provider APIs. Website markup, availability, route naming, and anti-bot protections can change; a live search may return no results when a source cannot be read. Source pages are linked where available. Prices and schedules should be checked with the provider before booking. The app does not bypass logins or CAPTCHAs and does not guarantee fare availability.

See [SCRAPERS.md](SCRAPERS.md) for scraper details and [SCRAPER_PLAN.md](SCRAPER_PLAN.md) for current scope and validation notes.
