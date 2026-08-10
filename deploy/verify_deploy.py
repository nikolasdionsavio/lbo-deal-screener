"""Promote gate for a Netlify deploy: check the ASSETS, not just the HTML.

A page can return HTTP 200 and still be broken. On 2026-08-09 a deploy shipped
HTML whose CSS bundle and three JS chunks were never uploaded: every route
answered 200 while the live site rendered as unstyled markup. Checking the
status code alone cannot catch that.

So for each route this fetches the HTML, extracts the hashed asset URLs the
document actually references, and requires every one of them to return 200.

    python deploy/verify_deploy.py https://<deploy-url> [/route ...]

Exits non-zero on the first failure, so it can gate a promote in a shell chain.
"""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = 45
DEFAULT_ROUTES = ["/", "/screen", "/about", "/company/AAPL/dashboard"]

# Hashed build assets emitted by Next.js. A missing one is invisible in the
# route's own status code but fatal on screen.
ASSET_PATTERN = re.compile(r'(?:href|src)="(/_next/static/[^"]+\.(?:css|js))"')


def fetch(url: str, attempts: int = 3) -> tuple[int, bytes]:
    """GET a URL. Retries network-level failures, never HTTP statuses.

    A freshly published deploy can refuse a connection for a moment, and
    checking dozens of assets in a row occasionally trips a transient reset.
    Those produced a spurious GATE FAILED, which is dangerous in its own way:
    a gate that cries wolf invites overriding it. An HTTP status is a real
    answer from the server and is never retried.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "deploy-verify"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, b""
        except Exception as exc:  # connection reset, DNS, timeout
            if attempt == attempts:
                print(f"    ERROR reaching {url}: {exc.__class__.__name__}")
                return 0, b""
            time.sleep(attempt * 1.5)
    return 0, b""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    base = sys.argv[1].rstrip("/")
    routes = sys.argv[2:] or DEFAULT_ROUTES

    failures: list[str] = []
    for route in routes:
        status, body = fetch(f"{base}{route}")
        if status != 200:
            print(f"  FAIL {status}  {route}")
            failures.append(f"{route} -> HTTP {status}")
            continue

        assets = sorted(set(ASSET_PATTERN.findall(body.decode("utf-8", "replace"))))
        bad = []
        for asset in assets:
            asset_status, _ = fetch(f"{base}{asset}")
            if asset_status != 200:
                bad.append(f"{asset} -> HTTP {asset_status}")
        if bad:
            print(f"  FAIL {route}: {len(bad)} of {len(assets)} assets missing")
            for entry in bad:
                print(f"         {entry}")
            failures.extend(bad)
        else:
            print(f"  OK   {route}  ({len(assets)} assets verified)")

    if failures:
        print(f"\nGATE FAILED: {len(failures)} problem(s). Do NOT promote.")
        return 1
    print("\nGATE PASSED: every route and referenced asset returned 200.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
