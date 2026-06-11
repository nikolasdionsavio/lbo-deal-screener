# LBO Deal Screener

A private equity style deal screening tool for public companies, with live global coverage (US, UK and EU listings) via Yahoo Finance and official SEC EDGAR fundamentals for US tickers.

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
    providers/      MockProvider, SecEdgarProvider, FmpProvider, YahooProvider, composites, factory
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
  tests/            pytest suite (208 tests)
frontend/ (Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts)
  app/              routes: /, /login, /register, /deals, /company/[ticker]/{dashboard,kpis,valuation,lbo,score,memo}
  components/       sidebar, UI kit, chart wrappers, per-page components
  lib/              typed API client, shared types, formatting, hooks, auth context
```

Request flow: provider fetch -> normalization to canonical financials -> calculation modules (KPIs, valuation, LBO, score, memo) -> FastAPI JSON API -> Next.js client.

### Data providers

Four providers, composed by a factory and controlled by `DATA_PROVIDER`:

- **YahooProvider**: global live data (US, UK and EU listings) via the `yfinance` library. No API key required. This uses unofficial Yahoo Finance endpoints; see the trade-off below.
- **SecEdgarProvider**: annual 10-K fundamentals from the official SEC EDGAR JSON API. No API key, but SEC requires a descriptive `User-Agent` header (`SEC_EDGAR_USER_AGENT`).
- **FmpProvider**: share price, market cap and company profile from Financial Modeling Prep (`FMP_API_KEY`).
- **PolygonProvider / AlphaVantageProvider / TiingoProvider**: optional key-gated market-data fallbacks for `live` mode (`POLYGON_API_KEY`, `ALPHAVANTAGE_API_KEY`, `TIINGO_API_KEY`). Quotes are tried in order FMP → Polygon → Alpha Vantage → Tiingo and the first provider with a quote wins; Tiingo supplies price only (no market cap/shares).
- **MockProvider**: bundled sample JSON in `backend/data/sample/`, clearly labelled "Sample data (illustrative figures)". No network calls.

Modes:

- `auto` (default): Yahoo when the `yfinance` package is installed (it is in `requirements.txt`), else EDGAR + FMP when `SEC_EDGAR_USER_AGENT` is set, else sample data with an explicit warning in every response.
- `yahoo`: Yahoo Finance for search, market data, profiles and fundamentals worldwide. When `SEC_EDGAR_USER_AGENT` is also set, fundamentals for US-style tickers (no exchange suffix) are upgraded to official SEC EDGAR data and the bundle is labelled "SEC EDGAR + Yahoo Finance"; if EDGAR fails, the app falls back to Yahoo fundamentals with a warning.
- `live`: SEC EDGAR fundamentals plus FMP market data (US only); errors if `SEC_EDGAR_USER_AGENT` is missing.
- `mock`: always sample data; the offline/dev mode and the pytest default.

**The unofficial-endpoint trade-off.** Yahoo Finance has no official public API; `yfinance` reads the same endpoints the Yahoo website uses. They can change or rate-limit without notice, and the figures are Yahoo's own normalization of company reports rather than the filings themselves. Every bundle served from Yahoo therefore carries the warning "Data from unofficial Yahoo Finance endpoints; verify figures against filings before relying on them.", which surfaces on each page and in memo data gaps. For US tickers, setting `SEC_EDGAR_USER_AGENT` replaces Yahoo fundamentals with official EDGAR data while keeping Yahoo quotes.

### Currency handling

Non-US listings introduce currencies. Quotes keep their listing currency (LSE pence quotes are normalized to pounds), fundamentals keep their reporting currency, and the API reports both. When the two differ (for example a company quoted in GBP that reports in USD), mixed-currency figures (enterprise value, EV multiples, P/E, FCF yield, premium vs current price) are suppressed with an explicit warning rather than silently mixing currencies; there is no FX conversion in the MVP. Single-currency outputs (KPIs, the LBO model, the implied valuation range) are unaffected, and all figures display the correct currency symbol or ISO code.

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
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Live global data works with zero keys: with `yfinance` installed (it is in `requirements.txt`), the default `auto` mode serves live US, UK and EU data via Yahoo Finance unofficial endpoints, so tickers like `AAPL`, `TSCO.L` or `ASML.AS` work out of the box. Set `DATA_PROVIDER=mock` for fully offline runs on the bundled sample data. Setting `SEC_EDGAR_USER_AGENT` is recommended so US-ticker fundamentals come from official SEC EDGAR filings instead of Yahoo. To configure anything, copy `.env.example` to `backend/.env` and edit it.

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
| `DATA_PROVIDER` | `auto`, `mock`, `live` or `yahoo` | `auto` | Set `mock` to force sample data, `yahoo` for keyless global live data, `live` for EDGAR + FMP |
| `SEC_EDGAR_USER_AGENT` | Descriptive User-Agent for SEC EDGAR requests | empty | Official US fundamentals (required for `live`; recommended for `yahoo`/`auto`) |
| `FMP_API_KEY` | Financial Modeling Prep API key | empty | Market data in `live` mode only (Yahoo modes need no key) |
| `POLYGON_API_KEY` | Polygon.io API key | empty | Optional `live`-mode market-data fallback (tried after FMP); free key at https://polygon.io |
| `ALPHAVANTAGE_API_KEY` | Alpha Vantage API key | empty | Optional `live`-mode market-data fallback (tried after Polygon); free key at https://www.alphavantage.co/support/#api-key |
| `TIINGO_API_KEY` | Tiingo API key | empty | Optional `live`-mode market-data fallback (tried last; price only); free key at https://www.tiingo.com |
| `CORS_ORIGINS` | Comma-separated allowed origins for the API | `http://localhost:3000` | Frontend served from another origin |
| `NEXT_PUBLIC_API_URL` | Base URL the browser uses to reach the API | `http://localhost:8000` | Frontend deployed apart from the API (set in `frontend/.env.local` or as a Docker build arg) |

### Getting live data

1. **Yahoo Finance** (global, no key): nothing to configure. With `yfinance` installed, `DATA_PROVIDER=auto` (the default) or `DATA_PROVIDER=yahoo` serves live search, quotes, profiles and fundamentals for US, UK and EU listings. These are unofficial endpoints; every response carries a warning to verify figures against filings.
2. **SEC EDGAR** (official US fundamentals, free, no key): set `SEC_EDGAR_USER_AGENT` to a descriptive string with contact details, as SEC requests, for example `LBO Deal Screener your_email@example.com`. In Yahoo modes this upgrades US-ticker fundamentals to official filings data.
3. **Financial Modeling Prep** (market data for `live` mode): create a free API key at https://site.financialmodelingprep.com/developer/docs and set `FMP_API_KEY`. Without it, live mode still serves EDGAR fundamentals but market-price-dependent figures (market cap, EV, valuation multiples) are reported as unavailable with warnings. Yahoo modes do not use FMP.

## Testing

```bash
cd backend
.venv/bin/python -m pytest -q
```

208 tests, all green. The suite covers KPI math, IRR/MoM, the LBO engine against an independent in-test reimplementation, scoring weight redistribution, valuation ranges, currency-mismatch suppression, memo generation, EDGAR normalization, the Yahoo provider (against faked yfinance objects; pytest never hits the live network) and auth/saved-deals CRUD.

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
