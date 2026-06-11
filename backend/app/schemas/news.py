"""Company news schemas (spec §19.6)."""

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """One headline. published_at is ISO-8601 so string sort = recency sort."""

    title: str
    url: str
    source: str | None = None
    published_at: str | None = None
    summary: str | None = None


class NewsResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/news (spec §19.6)."""

    ticker: str
    items: list[NewsItem] = Field(default_factory=list)
    provider: str
    warnings: list[str] = Field(default_factory=list)
