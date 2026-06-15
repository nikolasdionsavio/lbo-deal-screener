---
title: LBO Deal Screener API
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
short_description: FastAPI backend for the LBO Deal Screener
---

# LBO Deal Screener — API backend

FastAPI backend for the [LBO Deal Screener](https://nikolasproject.com). US-listed
company fundamentals from SEC EDGAR, market data from Financial Modeling Prep, traceable
KPIs, a five-year LBO model with sensitivities, peer comparables, filings, news, and a
deterministic investment memo.

This Space hosts the API only. The interface lives at https://nikolasproject.com.

Health check: `/api/health`. Interactive docs: `/docs`.

Hosted on Hugging Face Spaces (2 vCPU) for consistent low-latency responses; the
companion frontend is on Netlify.
