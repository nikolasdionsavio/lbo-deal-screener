# LBO Deal Screener

A private equity style deal screening tool for US-listed public companies.

Enter a ticker or company name and the app produces:

- **Search / landing** - debounced company search with sample-company quick links.
- **Company dashboard** - profile, share price, market cap, enterprise value, headline financials, data source and data date.
- **KPI dashboard** - 14 traceable KPIs (margins, growth, leverage, cash conversion, ROIC), each with formula, inputs, period and warnings, plus historical time series charts.
- **Valuation** - current trading multiples and an editable low/base/high EV/EBITDA range with implied equity value, implied share price and premium vs. current.
- **LBO model** - simplified 5-year (1-7 year) leveraged buyout model with editable assumptions, year-by-year debt schedule, IRR/MoM outputs and three 5x5 sensitivity grids.
- **Deal score** - transparent 0-100 screening score across six weighted components, each with a written reason citing the actual input values.
- **Investment memo** - deterministic, template-generated memo built only from computed data. No LLM, so it never invents facts; missing data is stated as missing.
- **Saved deals** - watchlist with snapshotted score, memo and LBO assumptions (email/password auth required for saving only; all analysis is public).

> **Disclaimer**
>
> This is a screening tool for educational and research purposes. It is **not investment advice**, and no valuation it produces is definitive. Outputs are mechanical calculations from public or sample data, with simplifying assumptions documented on each page. Every page shows its data source and data date, and every computed number is traceable to a formula and its inputs.

## Architecture

```
backend/  (FastAPI, Python 3.13)
  app/
    core/           settings from env vars (pydantic-settings)
    schemas/        all Pydantic models (company, financials, kpi, valuation, lbo, score, memo, deal, auth)
    providers/      MockProvider, SecEdgarProvider, FmpProvider, factory
    normalization/  raw provider payloads -> canonical FiscalYearFinancials
    kpis/           traceable KPI calculations
    valuation/      multiples + valuation range
    lbo/            LBO engine, IRR/MoM, sensitivities
    scoring/        0-100 deal score
    memo/           deterministic memo generation
    auth/           bcrypt password hashing, JWT (PyJWT), current-user dependency
    db/             SQLAlchemy 2.x engine/models (9 tables; SQLite or Postgres)
    crud/           persistence helpers (cache, saved deals, snapshots)
    services/       composition layer used by the routes
    api/            FastAPI routers (all under /api)
  data/sample/      bundled sample companies (AAPL, MSFT, HD, KO, DE, TESTCO)
  tests/            pytest suite (178 tests)
frontend/ (Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts)
  app/              routes: /, /login, /register, /deals, /company/[ticker]/{dashboard,kpis,valuation,lbo,score,memo}
  components/       sidebar, UI kit, chart wrappers, per-page components
  lib/              typed API client, shared types, formatting, hooks, auth context
```

Request flow: provider fetch -> normalization to canonical financials -> calculation modules (KPIs, valuation, LBO, score, memo) -> FastAPI JSON API -> Next.js client.

### Data providers

Three providers, composed by a factory and controlled by `DATA_PROVIDER`:

- **MockProvider** (default fallback): bundled sample JSON in `backend/data/sample/`, clearly labelled "Sample data (illustrative figures)". No network calls.
- **SecEdgarProvider**: annual 10-K fundamentals from the official SEC EDGAR JSON API. No API key, but SEC requires a descriptive `User-Agent` header (`SEC_EDGAR_USER_AGENT`).
- **FmpProvider**: share price, market cap and company profile from Financial Modeling Prep (`FMP_API_KEY`).

Modes: `mock` always uses sample data; `live` requires EDGAR + FMP configuration and errors otherwise; `auto` (default) uses live providers when `SEC_EDGAR_USER_AGENT` is set and otherwise falls back to sample data with an explicit warning in every response.

### What is and is not cached

- Provider fetches (company profile + annual financials) are write-through cached in the database with a 24-hour TTL. The cache is skipped in mock mode.
- KPIs, valuation, LBO runs, scores and memos are computed fresh on every request (they take milliseconds). Snapshot rows for score, memo and LBO assumptions are written only when a deal is saved or updated, so a saved deal preserves what you saw at save time.

## Quick start (no Docker)

This is the primary, verified path. It uses SQLite and two terminals; no database server or `.env` file is required.

Prerequisites:

- Python 3.13
- Node.js 18 or newer

The repository path may contain spaces, so quote it in shell commands.

### Backend (terminal 1)

```bash
cd backend
python3 -m venv .venv          # python3 must be a 3.13 interpreter; use python3.13 or a full path if needed
.venv/bin/pip install -r requirements.txt
DATA_PROVIDER=mock .venv/bin/uvicorn app.main:app --reload --port 8000
```

`DATA_PROVIDER=mock` forces the bundled sample data. The app also starts with no environment variables and no `.env` file at all: the default `auto` mode falls back to sample data and adds the warning "Using bundled sample data; set SEC_EDGAR_USER_AGENT and FMP_API_KEY for live data." to responses. To configure anything, copy `.env.example` to `backend/.env` and edit it.

### Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

### URLs

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Interactive API docs (Swagger UI): http://localhost:8000/docs

## Docker

```bash
docker compose up --build
```

This builds the backend (`python:3.13-slim`) and frontend (`node:20-alpine`, multi-stage) images and starts PostgreSQL 16, the API on port 8000 and the frontend on port 3000. `JWT_SECRET`, `DATA_PROVIDER`, `SEC_EDGAR_USER_AGENT` and `FMP_API_KEY` can be passed through from the host environment.

Honest caveat: the Dockerfiles and `docker-compose.yml` were validated by inspection only; Docker is not installed on the authoring machine, so the images have not been built here. The non-Docker path above is the verified one.

## Environment variables

All variables are documented in `.env.example`. Defaults are chosen so the app runs with no configuration at all.

| Variable | Meaning | Default | Needed when |
|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./lbo_screener.db` | Only to use Postgres (Docker compose sets it) |
| `JWT_SECRET` | HS256 signing secret for auth tokens | dev placeholder | Any non-throwaway deployment; generate 32+ random bytes |
| `DATA_PROVIDER` | `auto`, `mock` or `live` | `auto` | Set `mock` to force sample data, `live` to require real data |
| `SEC_EDGAR_USER_AGENT` | Descriptive User-Agent for SEC EDGAR requests | empty | Live fundamentals (`live`, or to activate `auto`) |
| `FMP_API_KEY` | Financial Modeling Prep API key | empty | Live market data (share price, market cap, profile) |
| `CORS_ORIGINS` | Comma-separated allowed origins for the API | `http://localhost:3000` | Frontend served from another origin |
| `NEXT_PUBLIC_API_URL` | Base URL the browser uses to reach the API | `http://localhost:8000` | Frontend deployed apart from the API (set in `frontend/.env.local` or as a Docker build arg) |

### Getting live data

1. **SEC EDGAR** (fundamentals, free, no key): set `SEC_EDGAR_USER_AGENT` to a descriptive string with contact details, as SEC requests, for example `LBO Deal Screener your_email@example.com`.
2. **Financial Modeling Prep** (market data): create a free API key at https://site.financialmodelingprep.com/developer/docs and set `FMP_API_KEY`. Without it, live mode still serves EDGAR fundamentals but market-price-dependent figures (market cap, EV, valuation multiples) are reported as unavailable with warnings.

With `DATA_PROVIDER=auto` (the default), setting `SEC_EDGAR_USER_AGENT` is what switches the app from sample data to live data.

## Testing

```bash
cd backend
.venv/bin/python -m pytest -q
```

178 tests, all green. The suite covers KPI math, IRR/MoM, the LBO engine against an independent in-test reimplementation, scoring weight redistribution, valuation ranges, memo generation, EDGAR normalization and auth/saved-deals CRUD.

Most expected values are hand-checkable because they run against **TESTCO**, a synthetic fixture company ("Testco Industrials Inc", `backend/data/sample/TESTCO.json`) with deliberately round numbers: FY2025 revenue $1,000m, EBITDA $250m, FCF $180m, net debt $300m, 100m shares at $13.50. TESTCO is excluded from search results but loadable by ticker, so the fixture is also usable for manual exploration.

## Project structure

```
PE_Deal_Analyser/
  .env.example
  docker-compose.yml
  docs/
    BUILD_SPEC.md        # canonical build specification
  backend/
    Dockerfile
    requirements.txt
    app/                 # FastAPI application (see Architecture)
    data/                # bundled sample company JSON
    tests/               # pytest suite
  frontend/
    Dockerfile
    package.json
    app/                 # Next.js App Router pages
    components/          # sidebar, UI kit, charts, page components
    lib/                 # API client, types, formatting, hooks, auth
```

## Roadmap

- PDF memo export
- Celery/Redis background data refresh
- Alembic migrations
- Additional data providers (Polygon, Alpha Vantage)
- Peer comparables
- Historical valuation multiples
- Deployment guides (Render, Railway)
- Revolver and tranche structure in the LBO model
- Quarterly data

## License and intent

Portfolio/educational project. Screening tool for educational and research purposes. Not investment advice.
