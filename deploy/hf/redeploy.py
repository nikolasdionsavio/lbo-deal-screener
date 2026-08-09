"""Redeploy the backend to the HF Space and (re)set its runtime config.

One command pushes the current backend code and updates the Space secrets that
have changed since the last full deploy:

  * CORS_ORIGINS / FRONTEND_URL / BACKEND_URL  — always set (constants below)
  * GOOGLE_/GITHUB_ client id + secret         — set only if present in env
  * RESEND_API_KEY                             — set only if present in env

It never deletes other secrets (DATABASE_URL, JWT_SECRET, FMP_API_KEY, ...),
so they survive untouched.

Run (HF_TOKEN required; provide whichever optional secrets you want to set):

    HF_TOKEN=hf_xxx \
    GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... \
    GITHUB_CLIENT_ID=... GITHUB_CLIENT_SECRET=... \
    python deploy/hf/redeploy.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

SPACE_ID = "nikolasdion/lbo-screener-api"

# Constants that should always reflect the current production wiring.
ALWAYS: dict[str, str] = {
    "CORS_ORIGINS": (
        "https://nikolasproject.com,"
        "https://www.nikolasproject.com,"
        "https://app.nikolasdionsavio.com"
    ),
    "FRONTEND_URL": "https://app.nikolasdionsavio.com",
    # OAuth redirect URIs are built from this. Pointed at the user's own domain,
    # which proxies /api/auth/oauth/* to this backend, so provider screens show
    # nikolasproject.com instead of the hf.space host.
    "BACKEND_URL": "https://nikolasproject.com",
}

# Set on the Space only when supplied in the environment (leave others as-is).
OPTIONAL_FROM_ENV = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "RESEND_API_KEY",
    # Gates /api/admin/* (announcements, screening-index rebuild).
    "ADMIN_TOKEN",
    # UK Companies House REST + document API.
    "COMPANIES_HOUSE_API_KEY",
    # Required by the SEC frames ingestion behind the screening index.
    "SEC_EDGAR_USER_AGENT",
]

COMMIT_MESSAGE = "Backend redeploy"

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
HF_README = Path(__file__).resolve().parent / "README.md"

IGNORE_PATTERNS = [
    "tests/**",
    ".venv/**",
    "**/__pycache__/**",
    "*.db",
    "*.sqlite3",
    ".pytest_cache/**",
    "README.md",
]


def main() -> None:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        sys.exit("Missing HF_TOKEN")
    api = HfApi(token=token)

    print("Setting runtime config secrets...")
    for key, value in ALWAYS.items():
        api.add_space_secret(repo_id=SPACE_ID, key=key, value=value)
        print(f"  set {key}")
    for key in OPTIONAL_FROM_ENV:
        value = os.environ.get(key, "").strip()
        if value:
            api.add_space_secret(repo_id=SPACE_ID, key=key, value=value)
            print(f"  set {key}")
        else:
            print(f"  skip {key} (not provided)")

    print("Uploading backend...")
    api.upload_folder(
        repo_id=SPACE_ID,
        repo_type="space",
        folder_path=str(BACKEND_DIR),
        ignore_patterns=IGNORE_PATTERNS,
        commit_message=os.environ.get("COMMIT_MESSAGE", COMMIT_MESSAGE),
    )
    print("Re-uploading Space README...")
    api.upload_file(
        repo_id=SPACE_ID,
        repo_type="space",
        path_or_fileobj=str(HF_README),
        path_in_repo="README.md",
        commit_message="Space metadata",
    )
    print("\nDone. The Space is rebuilding (a few minutes).")
    print("API: https://nikolasdion-lbo-screener-api.hf.space/api/health")
    print("Providers: https://nikolasdion-lbo-screener-api.hf.space/api/auth/oauth/providers")


if __name__ == "__main__":
    main()
