"""Assumption tracking models.

Every assumption used in the system must have an explicit status, source,
and version. No assumption may silently default to a convenient value.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class AssumptionStatus(str, Enum):
    """Lifecycle status of an assumption."""

    CONFIRMED = "confirmed"       # Verified against a primary source
    UNRESOLVED = "unresolved"     # Requires clarification before use
    ASSUMED = "assumed"           # Working assumption; source is noted
    INAPPLICABLE = "inapplicable" # Not relevant for this client/scenario


class UnresolvedStatus(str, Enum):
    """Used where a specific field value is unknown and must not be fabricated."""

    UNRESOLVED = "unresolved"


class Assumption(BaseModel):
    """A single tracked assumption.

    Fields
    ------
    id:          Unique slug, e.g. ``annuity_vanguard_rate_interpretation``.
    description: Human-readable description of what is assumed.
    value:       The assumed value, or None if unresolved.
    status:      Lifecycle status.
    source:      Where the value came from (document, conversation, etc.).
    version:     Document or data version, if applicable.
    notes:       Any additional context or outstanding questions.
    """

    id: str
    description: str
    value: Optional[Any] = None
    status: AssumptionStatus
    source: Optional[str] = None
    version: Optional[str] = None
    notes: Optional[str] = None


class AssumptionsRegister(BaseModel):
    """Container for all assumptions used in a scenario or analysis run."""

    assumptions: list[Assumption] = Field(default_factory=list)

    def get(self, assumption_id: str) -> Optional[Assumption]:
        """Return an assumption by ID, or None if not found."""
        for a in self.assumptions:
            if a.id == assumption_id:
                return a
        return None

    def unresolved(self) -> list[Assumption]:
        """Return all assumptions that are still unresolved."""
        return [a for a in self.assumptions if a.status == AssumptionStatus.UNRESOLVED]

    def add(self, assumption: Assumption) -> None:
        """Add an assumption; raises ValueError if ID already exists."""
        if any(a.id == assumption.id for a in self.assumptions):
            raise ValueError(f"Assumption '{assumption.id}' already registered.")
        self.assumptions.append(assumption)
