"""Build or refresh the US screening index from the SEC frames API.

Run this against the production database directly. The SEC calls come from
wherever this runs, so a local run avoids the rate limiting that shared cloud
egress IPs attract, and the app simply reads the table afterwards.

    # dry run against a local SQLite file
    SEC_EDGAR_USER_AGENT="Your Name you@example.com" \
        python scripts/build_screen_index.py

    # against production
    DATABASE_URL="postgresql://..." \
    SEC_EDGAR_USER_AGENT="Your Name you@example.com" \
        python scripts/build_screen_index.py --sectors

Flags:
    --periods CY2025,CY2024   Periods to pull, newest first.
    --sectors                 Also fill missing SIC sectors (one request per
                              company, so the first full run takes minutes).
    --sector-limit N          Cap the sector pass, for incremental runs.
    --all-filers              Keep filers with no listed ticker (default: drop).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Allow running as a plain script from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.base import SessionLocal, init_db  # noqa: E402
from app.screening.frames import SecFramesClient  # noqa: E402
from app.screening.index_service import (  # noqa: E402
    DEFAULT_PERIODS,
    coverage_summary,
    enrich_missing_sectors,
    rebuild_index,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS))
    parser.add_argument("--sectors", action="store_true")
    parser.add_argument("--sector-limit", type=int, default=None)
    parser.add_argument("--all-filers", action="store_true")
    args = parser.parse_args()

    user_agent = (
        settings.sec_edgar_user_agent
        or os.environ.get("SEC_EDGAR_USER_AGENT", "")
    ).strip()
    if not user_agent:
        sys.exit(
            "SEC_EDGAR_USER_AGENT is required (the SEC rejects requests without "
            "a contact string, e.g. 'Your Name you@example.com')."
        )

    periods = tuple(p.strip() for p in args.periods.split(",") if p.strip())
    print(f"Database: {settings.database_url.split('@')[-1][:60]}")
    print(f"Periods:  {', '.join(periods)}")

    init_db()
    client = SecFramesClient(user_agent)
    db = SessionLocal()
    try:
        started = time.monotonic()
        print("\nFetching SEC frames (4 tags per period)...")
        result = rebuild_index(
            db, client, periods=periods, listed_only=not args.all_filers
        )
        print(
            f"  filers with revenue: {result.fetched:,}\n"
            f"  listed (kept):       {result.listed:,}\n"
            f"  rows written:        {result.written:,}\n"
            f"  elapsed:             {time.monotonic() - started:.1f}s"
        )

        if args.sectors:
            print("\nFilling missing sectors (1 request per company)...")
            enriched = enrich_missing_sectors(db, client, limit=args.sector_limit)
            print(f"  companies enriched: {enriched:,}")

        summary = coverage_summary(db)
        print(
            f"\nIndex coverage\n"
            f"  total rows:            {summary['total']:,}\n"
            f"  revenue + EBITDA:      {summary['with_ebitda']:,}\n"
            f"  revenue + EBIT only:   {summary['ebit_only']:,}\n"
            f"  revenue only:          {summary['revenue_only']:,}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
