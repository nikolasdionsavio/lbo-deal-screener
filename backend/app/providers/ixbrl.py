"""Parse a UK Companies House iXBRL accounts document into headline figures.

Companies House accounts are filed as inline XBRL (XHTML with <ix:nonFraction>
tags carrying FRC-taxonomy concepts). This extracts the headline P&L and balance
figures for the LATEST reported period, honestly: only what is actually tagged.

Reality this module encodes:
- Small / micro companies file NO profit-and-loss account (small-company
  exemption), so turnover / operating profit are simply absent. We return None
  for those and let the caller show "not disclosed", never a guess.
- EBITDA is never a filed FRC tag. We do NOT invent it here; a caller may
  approximate it as operating profit + depreciation/amortisation when both are
  disclosed, and must label it as derived.
- Values carry a `scale` (power of ten) and `sign` on the tag; both are applied.

No network, no API key: this is pure parsing, unit-tested against a fixture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# FRC-taxonomy local names (namespace prefix stripped) for each headline figure,
# in preference order. Filers use several taxonomies (FRS 102 / FRS 105 / full
# IFRS) with slightly different names, so each field lists the known variants.
_CONCEPTS: dict[str, list[str]] = {
    "turnover": ["TurnoverRevenue", "Turnover", "TurnoverGrossOperatingRevenue", "Revenue"],
    "gross_profit": ["GrossProfitLoss"],
    "operating_profit": ["OperatingProfitLoss"],
    "profit_before_tax": [
        "ProfitLossOnOrdinaryActivitiesBeforeTax",
        "ProfitLossBeforeTax",
    ],
    "profit_for_period": ["ProfitLoss", "ProfitLossForPeriod"],
    "depreciation_amortisation": [
        "DepreciationAmortisationImpairmentExpense",
        "DepreciationExpense",
        "DepreciationOfPropertyPlantEquipment",
    ],
    "net_assets": ["NetAssetsLiabilities", "NetAssetsLiabilitiesIncludingPensionAssetLiability"],
    "cash": ["CashBankOnHand", "CashBankInHand", "CashCashEquivalents"],
    "total_equity": ["Equity", "ShareholdersFunds"],
}


@dataclass
class IxbrlAccounts:
    """Headline figures for the latest reported period. None = not disclosed."""

    period_end: str | None
    turnover: float | None
    gross_profit: float | None
    operating_profit: float | None
    profit_before_tax: float | None
    profit_for_period: float | None
    net_assets: float | None
    cash: float | None
    total_equity: float | None
    currency: str | None
    # True when the accounts carry no P&L at all (small-company exemption).
    no_profit_and_loss: bool


def _local_name(concept: str) -> str:
    """`uk-bus:Turnover` / `ns5:Turnover` -> `Turnover`."""
    return concept.split(":")[-1] if concept else ""


def _parse_number(raw: str, scale: str | None, sign: str | None) -> float | None:
    """iXBRL numeric: strip formatting, apply scale (power of ten) and sign."""
    text = re.sub(r"[,\s ]", "", raw or "").strip()
    if text in {"", "-", "—"}:
        return None
    # Bracketed negatives, e.g. "(1,234)".
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        value = float(text)
    except ValueError:
        return None
    if scale:
        try:
            value *= 10 ** int(scale)
        except ValueError:
            pass
    if sign == "-" or negative:
        value = -abs(value)
    return value


def _context_end_dates(soup: BeautifulSoup) -> dict[str, str]:
    """Map each context id to its period end (or instant) ISO date."""
    ends: dict[str, str] = {}
    for ctx in soup.find_all(re.compile(r"(^|:)context$", re.I)):
        cid = ctx.get("id")
        if not cid:
            continue
        end = ctx.find(re.compile(r"(^|:)enddate$", re.I))
        instant = ctx.find(re.compile(r"(^|:)instant$", re.I))
        node = end or instant
        if node and node.get_text(strip=True):
            ends[cid] = node.get_text(strip=True)
    return ends


def parse_ixbrl_accounts(content: bytes | str) -> IxbrlAccounts:
    """Parse an iXBRL accounts document into headline figures for the latest
    period. Returns Nones (and no_profit_and_loss=True) when the P&L is absent."""
    soup = BeautifulSoup(content, "html.parser")
    context_end = _context_end_dates(soup)

    # Collect every tagged numeric fact: local concept name -> list of
    # (period_end, value, currency), so we can pick the latest period per field.
    facts: dict[str, list[tuple[str, float, str | None]]] = {}
    for tag in soup.find_all(re.compile(r"nonfraction$", re.I)):
        concept = _local_name(tag.get("name", ""))
        if not concept:
            continue
        value = _parse_number(
            tag.get_text(), tag.get("scale"), tag.get("sign")
        )
        if value is None:
            continue
        end = context_end.get(tag.get("contextref", ""), "")
        unit = tag.get("unitref")
        currency = None
        if unit:
            m = re.search(r"(GBP|USD|EUR)", unit, re.I)
            currency = m.group(1).upper() if m else None
        facts.setdefault(concept, []).append((end, value, currency))

    def pick(field: str) -> tuple[float | None, str | None, str | None]:
        """Latest-period value for a field across its concept variants."""
        best: tuple[str, float, str | None] | None = None
        for concept in _CONCEPTS[field]:
            for end, value, currency in facts.get(concept, []):
                if best is None or end > best[0]:
                    best = (end, value, currency)
        if best is None:
            return None, None, None
        return best[1], best[0], best[2]

    turnover, t_end, t_ccy = pick("turnover")
    gross_profit, _, _ = pick("gross_profit")
    operating_profit, op_end, op_ccy = pick("operating_profit")
    profit_before_tax, _, _ = pick("profit_before_tax")
    profit_for_period, p_end, p_ccy = pick("profit_for_period")
    net_assets, na_end, na_ccy = pick("net_assets")
    cash, _, _ = pick("cash")
    total_equity, _, _ = pick("total_equity")

    period_end = t_end or op_end or p_end or na_end
    currency = t_ccy or op_ccy or p_ccy or na_ccy
    no_pl = turnover is None and operating_profit is None and profit_for_period is None

    return IxbrlAccounts(
        period_end=period_end or None,
        turnover=turnover,
        gross_profit=gross_profit,
        operating_profit=operating_profit,
        profit_before_tax=profit_before_tax,
        profit_for_period=profit_for_period,
        net_assets=net_assets,
        cash=cash,
        total_equity=total_equity,
        currency=currency,
        no_profit_and_loss=no_pl,
    )
