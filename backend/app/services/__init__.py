"""Composition layer used by API routes (spec §3, §12)."""

from app.services import company_service, deal_service

__all__ = ["company_service", "deal_service"]
