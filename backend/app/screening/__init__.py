"""US screening index: cross-company financials from the SEC frames API.

Unlike the per-company providers, this package builds a SCREENABLE index: one
row per US filer holding revenue, operating income, D&A and a calculated
EBITDA, so the app can answer "which companies have revenue of $3-20m and
positive EBITDA" without fetching each company individually.
"""
