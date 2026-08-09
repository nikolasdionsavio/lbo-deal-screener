"""iXBRL accounts parser: headline extraction, scale/sign, small-company no-P&L.

Fixture-driven, no network. The snippets mimic real Companies House iXBRL:
<ix:nonFraction> facts carrying FRC-taxonomy concepts, referencing contexts
whose period end dates disambiguate current vs prior year.
"""

from app.providers.ixbrl import parse_ixbrl_accounts

# A medium company filing FULL accounts: two years of turnover (pick the latest),
# operating profit, profit for the year (bracketed negative), net assets. GBP in
# thousands (scale="3").
FULL_ACCOUNTS = """
<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:xbrli="http://www.xbrl.org/2003/instance">
  <body>
    <xbrli:context id="cur">
      <xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>
      <xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period>
    </xbrli:context>
    <xbrli:context id="prev">
      <xbrli:period><xbrli:startDate>2023-01-01</xbrli:startDate>
      <xbrli:endDate>2023-12-31</xbrli:endDate></xbrli:period>
    </xbrli:context>
    <xbrli:context id="inst">
      <xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>
    </xbrli:context>
    <ix:nonFraction name="uk-bus:Turnover" contextRef="prev" unitRef="GBP" scale="3">10,000</ix:nonFraction>
    <ix:nonFraction name="uk-bus:Turnover" contextRef="cur" unitRef="GBP" scale="3">12,500</ix:nonFraction>
    <ix:nonFraction name="uk-core:OperatingProfitLoss" contextRef="cur" unitRef="GBP" scale="3">1,800</ix:nonFraction>
    <ix:nonFraction name="uk-core:ProfitLoss" contextRef="cur" unitRef="GBP" scale="3" sign="-">450</ix:nonFraction>
    <ix:nonFraction name="uk-bus:NetAssetsLiabilities" contextRef="inst" unitRef="GBP" scale="3">8,200</ix:nonFraction>
  </body>
</html>
"""

# A small company using the exemption: balance sheet only, NO profit and loss.
SMALL_ACCOUNTS = """
<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:xbrli="http://www.xbrl.org/2003/instance">
  <body>
    <xbrli:context id="inst">
      <xbrli:period><xbrli:instant>2024-03-31</xbrli:instant></xbrli:period>
    </xbrli:context>
    <ix:nonFraction name="uk-bus:NetAssetsLiabilities" contextRef="inst" unitRef="GBP" scale="0">432100</ix:nonFraction>
    <ix:nonFraction name="uk-bus:CashBankOnHand" contextRef="inst" unitRef="GBP" scale="0">128000</ix:nonFraction>
  </body>
</html>
"""


def test_full_accounts_headline_figures() -> None:
    a = parse_ixbrl_accounts(FULL_ACCOUNTS)
    # Latest turnover is the current year, scaled from thousands.
    assert a.turnover == 12_500_000
    assert a.operating_profit == 1_800_000
    # Bracket/sign negative applied.
    assert a.profit_for_period == -450_000
    assert a.net_assets == 8_200_000
    assert a.period_end == "2024-12-31"
    assert a.currency == "GBP"
    assert a.no_profit_and_loss is False


def test_small_company_has_no_profit_and_loss() -> None:
    a = parse_ixbrl_accounts(SMALL_ACCOUNTS)
    assert a.turnover is None
    assert a.operating_profit is None
    assert a.profit_for_period is None
    assert a.no_profit_and_loss is True
    # Balance-sheet items are still available (scale 0 = as-is).
    assert a.net_assets == 432_100
    assert a.cash == 128_000
    assert a.period_end == "2024-03-31"
