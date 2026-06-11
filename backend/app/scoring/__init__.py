"""Transparent deal score (spec §9)."""

from app.scoring.model import (
    COMPONENT_SPECS,
    ComponentSpec,
    InputSpec,
    compute_score,
    linear_score,
    rating_for,
)

__all__ = [
    "COMPONENT_SPECS",
    "ComponentSpec",
    "InputSpec",
    "compute_score",
    "linear_score",
    "rating_for",
]
