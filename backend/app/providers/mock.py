"""MockProvider: serves bundled sample JSON as CompanyDataBundle (spec §5).

Sample files live in ``backend/data/sample/*.json`` and mirror the
CompanyDataBundle schema. The path is resolved relative to this file so the
provider works regardless of the process working directory. TESTCO is a test
fixture: it is excluded from search results but remains loadable by ticker.
"""

import json
from pathlib import Path

import pydantic

from app.normalization import normalize_financials
from app.providers.base import DataProvider
from app.providers.exceptions import CompanyNotFoundError, ProviderError
from app.schemas.company import CompanyDataBundle, SearchResult

_BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_DIR = _BACKEND_DIR / "data" / "sample"

_HIDDEN_TICKERS = {"TESTCO"}


class MockProvider(DataProvider):
    name = "mock"

    def __init__(
        self,
        data_dir: Path | str | None = None,
        extra_warnings: list[str] | None = None,
    ) -> None:
        self._data_dir = Path(data_dir) if data_dir is not None else DEFAULT_SAMPLE_DIR
        self._extra_warnings = list(extra_warnings or [])
        self._bundles: dict[str, CompanyDataBundle] | None = None

    def _load_bundles(self) -> dict[str, CompanyDataBundle]:
        if self._bundles is not None:
            return self._bundles
        if not self._data_dir.is_dir():
            raise ProviderError(f"Sample data directory not found: {self._data_dir}")
        bundles: dict[str, CompanyDataBundle] = {}
        for path in sorted(self._data_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                bundle = CompanyDataBundle.model_validate(raw)
            except (ValueError, pydantic.ValidationError) as exc:
                raise ProviderError(f"Invalid sample data file {path.name}: {exc}") from exc
            bundles[bundle.info.ticker.upper()] = bundle
        if not bundles:
            raise ProviderError(f"No sample data files found in {self._data_dir}")
        self._bundles = bundles
        return bundles

    def search(self, query: str) -> list[SearchResult]:
        q = query.strip().lower()
        if not q:
            return []
        results: list[SearchResult] = []
        for ticker, bundle in sorted(self._load_bundles().items()):
            if ticker in _HIDDEN_TICKERS:
                continue
            if q in ticker.lower() or q in bundle.info.name.lower():
                results.append(
                    SearchResult(
                        ticker=bundle.info.ticker,
                        name=bundle.info.name,
                        exchange=bundle.info.exchange,
                        source=self.name,
                    )
                )
        return results

    def get_company(self, ticker: str) -> CompanyDataBundle:
        cached = self._load_bundles().get(ticker.strip().upper())
        if cached is None:
            available = ", ".join(sorted(self._load_bundles()))
            raise CompanyNotFoundError(
                f"Unknown ticker '{ticker}'. Available sample tickers: {available}."
            )
        # Deep copy so callers can never mutate the in-memory cache.
        bundle = cached.model_copy(deep=True)
        bundle.financials = normalize_financials(
            sorted(bundle.financials, key=lambda y: y.fiscal_year)[-5:]
        )
        for warning in self._extra_warnings:
            if warning not in bundle.warnings:
                bundle.warnings.append(warning)
        return bundle
