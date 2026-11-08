"""Transition instruction models.

A TransitionInstruction describes what to do with a holding during a portfolio
transition. Illiquid holdings must be explicitly excluded or marked RETAINED.
Not every asset can be fractionally transitioned.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransitionAction(str, Enum):
    """The action to take on a holding during transition."""

    SELL_ALL = "sell_all"
    SELL_PARTIAL = "sell_partial"
    RETAIN = "retain"           # Keep in portfolio unchanged
    CONVERT = "convert"         # e.g. Traditional IRA → Roth (tax event)
    EXCHANGE = "exchange"       # In-kind or 1035 exchange
    DEFERRED = "deferred"       # Transition planned for a future date
    REVIEW = "review"           # Requires human review before action


class TransitionEligibility(str, Enum):
    """Whether a holding can be transitioned."""

    ELIGIBLE = "eligible"
    INELIGIBLE_ILLIQUID = "ineligible_illiquid"
    INELIGIBLE_SURRENDER = "ineligible_surrender"   # In annuity surrender period
    INELIGIBLE_FRACTIONAL = "ineligible_fractional" # Cannot be partially sold
    UNKNOWN = "unknown"
    REVIEW_REQUIRED = "review_required"


class TransitionInstruction(BaseModel):
    """A single transition instruction for one holding.

    Business rules enforced at validation time (not here):
    - ILLIQUID holdings must not have action SELL_ALL or SELL_PARTIAL.
    - SELL_PARTIAL requires a fraction and the holding must be fractionally eligible.
    - CONVERT is only valid for TRADITIONAL_IRA → ROTH_IRA transitions.

    Fields
    ------
    instruction_id:   Unique identifier.
    holding_id:       The holding being transitioned.
    action:           What to do.
    fraction:         For SELL_PARTIAL — proportion to sell (0 < fraction < 1).
    target_product_id: Product to move into, if applicable.
    target_account_id: Account to receive the proceeds, if applicable.
    eligibility:      Pre-checked eligibility status.
    staged_date:      ISO-8601 date for DEFERRED instructions.
    notes:            Unresolved items or context.
    """

    instruction_id: str
    holding_id: str
    action: TransitionAction
    fraction: Optional[Decimal] = Field(
        None,
        description="Proportion to sell for SELL_PARTIAL (0 < fraction <= 1).",
    )
    target_product_id: Optional[str] = None
    target_account_id: Optional[str] = None
    eligibility: TransitionEligibility = TransitionEligibility.UNKNOWN
    staged_date: Optional[str] = None
    notes: Optional[str] = None
