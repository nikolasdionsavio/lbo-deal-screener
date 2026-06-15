"""Deploy the LBO Deal Screener API backend to a Hugging Face Docker Space.

Hugging Face Spaces free hardware = 2 vCPU + 16GB RAM, no credit card — about
20x the CPU of Render's free tier, which is what made search reliably fast.

Run (from repo root, with the backend venv active or any Python with
huggingface_hub installed):

    HF_TOKEN=hf_xxx \
    HF_SPACE_ID=your-username/lbo-screener-api \
    DATABASE_URL='postgresql+psycopg2://...' \
    JWT_SECRET='...' \
    FMP_API_KEY='...' \
    SEC_EDGAR_USER_AGENT='LBO Deal Screener you@example.com' \
    CORS_ORIGINS='https://nikolasproject.com,https://www.nikolasproject.com' \
    python deploy/hf/deploy.py

The script creates the Space (if needed), uploads the backend (app/, data/,
requirements.txt, Dockerfile) plus the HF Space README, and sets each secret.
The build/run is then automatic; the API comes up at
https://<user>-<space>.hf.space (slashes in the id become hyphens).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
HF_README = Path(__file__).resolve().parent / "README.md"

# Uploaded to the Space repo root; junk and local-only artifacts excluded.
IGNORE_PATTERNS = [
    "tests/**",
    ".venv/**",
    "**/__pycache__/**",
    "*.db",
    "*.sqlite3",
    ".pytest_cache/**",
    "README.md",  # replaced by the HF Space README below
]

SECRET_KEYS = [
    "DATABASE_URL",
    "JWT_SECRET",
    "FMP_API_KEY",
    "SEC_EDGAR_USER_AGENT",
    "CORS_ORIGINS",
]
# DATA_PROVIDER is a plain variable (not secret); default to live.
DATA_PROVIDER = os.environ.get("DATA_PROVIDER", "live")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    token = _require("HF_TOKEN")
    space_id = _require("HF_SPACE_ID")
    api = HfApi(token=token)

    print(f"Creating/ensuring Space {space_id} (docker sdk)...")
    api.create_repo(
        repo_id=space_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
    )

    print("Uploading backend (app/, data/, requirements.txt, Dockerfile)...")
    api.upload_folder(
        repo_id=space_id,
        repo_type="space",
        folder_path=str(BACKEND_DIR),
        ignore_patterns=IGNORE_PATTERNS,
        commit_message="Deploy LBO Deal Screener API backend",
    )

    print("Uploading HF Space README (metadata + app_port)...")
    api.upload_file(
        repo_id=space_id,
        repo_type="space",
        path_or_fileobj=str(HF_README),
        path_in_repo="README.md",
        commit_message="Space metadata",
    )

    print("Setting secrets and variables...")
    api.add_space_variable(repo_id=space_id, key="DATA_PROVIDER", value=DATA_PROVIDER)
    for key in SECRET_KEYS:
        api.add_space_secret(repo_id=space_id, key=key, value=_require(key))

    user = space_id.split("/")[0]
    name = space_id.split("/")[1]
    url = f"https://{user}-{name}.hf.space".lower()
    print("\nDone. The Space is building now (a few minutes).")
    print(f"API base URL: {url}")
    print(f"Health:       {url}/api/health")
    print(f"Space page:   https://huggingface.co/spaces/{space_id}")


if __name__ == "__main__":
    main()
