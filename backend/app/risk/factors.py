"""Extract the company's own disclosed risk factors from its latest 10-K
(SEC Item 1A), verbatim — never LLM-summarised.

Best-effort: 10-K HTML varies by filer, so extraction can fail; on failure the
caller falls back to a link to the filing. Each risk-factor caption is
keyword-categorised into the risk taxonomy (deterministic dictionaries), and the
"going concern" phrase is flagged specifically.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["extract_risk_factors", "categorise"]

_MAX_FACTORS = 40
_MAX_BYTES = 12_000_000  # cap the download; some 10-Ks are large
# Modern 10-Ks (e.g. Apple) bold captions via inline CSS, not <b>/<strong>.
_BOLD_STYLE = re.compile(r"font-weight:\s*(?:bold|[6-9]00)", re.I)

# Category keyword dictionaries, applied in priority order (first match wins).
_CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("Financial & liquidity", (
        "indebtedness", "our debt", "covenant", "going concern", "liquidity",
        "impairment", "goodwill", "dilution", "financing", "credit rating",
        "interest rate", "leverage", "capital requirements",
    )),
    ("Regulatory & legal", (
        "regulation", "regulatory", "compliance", "litigation", "legal proceeding",
        "lawsuit", "government", "tariff", "antitrust", "sanction", "license",
        "intellectual property", "patent", "tax law", "data privacy", "gdpr",
    )),
    ("Competition", (
        "competition", "competitor", "competitive", "market share",
        "pricing pressure", "substitute product",
    )),
    ("Cyber & technology", (
        "cybersecurity", "cyber", "data breach", "information systems",
        "security breach", "system failure", "artificial intelligence",
    )),
    ("Supply chain", (
        "supplier", "supply chain", "raw material", "component", "manufacturing",
        "procurement", "third-party manufacturer", "shortage",
    )),
    ("Customer concentration", (
        "significant customer", "limited number of customers", "customer concentration",
        "key customers", "loss of a customer", "concentration of",
    )),
    ("Macro & geopolitical", (
        "economic conditions", "inflation", "recession", "geopolitical",
        "foreign currency", "exchange rate", "war", "pandemic", "macroeconomic",
        "global economic",
    )),
    ("International", (
        "international operations", "foreign operations", "china", "emerging markets",
        "outside the united states", "cross-border",
    )),
    ("People & operations", (
        "key personnel", "attract and retain", "management team", "labor",
        "workforce", "talent", "operational", "disruption",
    )),
    ("Environmental & ESG", (
        "climate", "environmental", "sustainability", "emissions", "esg",
    )),
]


def categorise(heading: str) -> str:
    text = heading.lower()
    for name, keywords in _CATEGORIES:
        if any(k in text for k in keywords):
            return name
    return "Other"


def _looks_like_risk_heading(text: str) -> bool:
    """Heuristic: a real risk-factor caption is a medium-length sentence, not a
    section title, page number or boilerplate."""
    t = text.strip()
    if not (25 <= len(t) <= 320):
        return False
    lowered = t.lower()
    if lowered in ("risk factors", "item 1a. risk factors", "summary of risk factors"):
        return False
    if lowered.startswith("item ") or lowered.startswith("table of contents"):
        return False
    if t.isupper():  # ALL-CAPS is almost always a section banner
        return False
    # Risk-factor captions overwhelmingly read as statements/conditionals.
    return bool(re.search(r"\b(may|could|might|would|will|if|risk|adversely|failure|unable|depend|subject to)\b", lowered))


def _isolate_item_1a(text: str) -> str | None:
    """Return the Item 1A Risk Factors section text (last occurrence of the
    heading through to Item 1B / Item 2)."""
    # Normalise whitespace for boundary matching.
    starts = [m.end() for m in re.finditer(r"item\s*1a\.?\s*risk\s*factors", text, re.I)]
    if not starts:
        return None
    start = starts[-1]  # skip the table-of-contents reference
    end_match = re.search(r"item\s*1b\.?|item\s*2\.?\s*propert", text[start:], re.I)
    end = start + end_match.start() if end_match else min(len(text), start + 400_000)
    section = text[start:end]
    return section if len(section) > 500 else None


def extract_risk_factors(
    filing_url: str, user_agent: str
) -> tuple[list[dict[str, str]], bool] | None:
    """Fetch a 10-K and return (risk factors [{heading, category}], going_concern).

    None on any failure so the caller degrades to a filing link.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.get(
                filing_url,
                headers={"User-Agent": user_agent or "research contact@example.com"},
            )
            resp.raise_for_status()
            html = resp.text[:_MAX_BYTES]
    except Exception:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        # Candidate headings: each 10-K risk caption is bold, via a <b>/<strong>
        # tag OR (common in modern filings) an inline font-weight CSS style.
        bold_texts: list[str] = []
        for el in soup.find_all(["b", "strong"]):
            txt = " ".join(el.get_text(" ", strip=True).split())
            if txt:
                bold_texts.append(txt)
        for el in soup.find_all(style=_BOLD_STYLE):
            txt = " ".join(el.get_text(" ", strip=True).split())
            if txt:
                bold_texts.append(txt)
        full_text = " ".join(soup.get_text(" ", strip=True).split())
    except Exception:
        return None

    going_concern = bool(re.search(r"going concern", full_text, re.I))

    section = _isolate_item_1a(full_text)
    if section is None:
        # Could not isolate Item 1A; still return going-concern signal + no factors.
        return [], going_concern

    # Keep bold captions that fall inside (or read like) Item 1A risk factors.
    section_lower = section.lower()
    seen: set[str] = set()
    factors: list[dict[str, str]] = []
    for txt in bold_texts:
        if not _looks_like_risk_heading(txt):
            continue
        key = txt.lower()[:80]
        if key in seen:
            continue
        # Only keep captions whose text appears in the Item 1A section.
        if txt.lower()[:60] not in section_lower:
            continue
        seen.add(key)
        factors.append({"heading": txt, "category": categorise(txt)})
        if len(factors) >= _MAX_FACTORS:
            break

    return factors, going_concern
