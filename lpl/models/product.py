"""Investment product and fee structure models.

Key design rule: annuity rate terms are NOT interchangeable.
- payout_rate: percentage of account balance distributed annually as income.
- guaranteed_interest_rate: crediting rate applied to the account balance.
- withdrawal_rate: maximum percentage withdrawable per year without surrender charge.

The reference dossier uses "3% fixed lifetime income" and "3.25%" — the
economic meaning of these figures is UNRESOLVED and must not be assumed.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from lpl.models.assumptions import UnresolvedStatus


class RateInterpretation(str, Enum):
    """How an annuity rate figure should be interpreted.

    UNRESOLVED means the dossier description cannot be mapped to a specific
    economic concept without further clarification from the product provider.
    """

    PAYOUT_RATE = "payout_rate"
    GUARANTEED_INTEREST_RATE = "guaranteed_interest_rate"
    WITHDRAWAL_RATE = "withdrawal_rate"
    UNRESOLVED = "unresolved"


class AnnuityTerms(BaseModel):
    """Annuity-specific terms.

    These fields must NEVER be conflated. A calculation requiring one of them
    must check that the correct field is populated and that rate_interpretation
    is not UNRESOLVED before proceeding.

    Fields
    ------
    payout_rate:               % of balance paid as income per year (if known).
    guaranteed_interest_rate:  Crediting rate applied to balance (if known).
    withdrawal_rate:           Max free withdrawal % per year (if known).
    rate_description:          Raw string from the dossier (preserved verbatim).
    rate_interpretation:       Resolved interpretation, or UNRESOLVED.
    surrender_period_years:    Years remaining in surrender period (if applicable).
    """

    payout_rate: Optional[Decimal] = Field(
        None, description="Annual payout as % of account balance (decimal fraction, e.g. 0.03)."
    )
    guaranteed_interest_rate: Optional[Decimal] = Field(
        None, description="Annual crediting rate applied to balance (decimal fraction)."
    )
    withdrawal_rate: Optional[Decimal] = Field(
        None, description="Max free withdrawal % per year (decimal fraction)."
    )
    rate_description: str = Field(
        ..., description="Verbatim rate description from the product dossier."
    )
    rate_interpretation: RateInterpretation = RateInterpretation.UNRESOLVED
    surrender_period_years: Optional[int] = None

    @field_validator("payout_rate")
    @classmethod
    def _payout_rate_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"payout_rate must be >= 0 when provided, got {v}.")
        return v

    @field_validator("guaranteed_interest_rate")
    @classmethod
    def _guaranteed_interest_rate_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"guaranteed_interest_rate must be >= 0 when provided, got {v}.")
        return v

    @field_validator("withdrawal_rate")
    @classmethod
    def _withdrawal_rate_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"withdrawal_rate must be >= 0 when provided, got {v}.")
        return v

    @field_validator("surrender_period_years")
    @classmethod
    def _surrender_period_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError(f"surrender_period_years must be >= 0 when provided, got {v}.")
        return v


class FeeStructure(BaseModel):
    """Fee structure for an investment product or account.

    One-time and recurring fees are kept separate.

    Fields
    ------
    expense_ratio:        Annual recurring cost as decimal (e.g. 0.0075).
    advisory_fee_annual:  Annual advisor fee as decimal (recurring).
    exit_cost_pct:        One-time exit/redemption cost as decimal.
    entry_cost_pct:       One-time entry/load cost as decimal.
    other_one_time:       Any other one-time costs in USD.
    other_recurring:      Any other annual recurring costs in USD.
    notes:                Unresolved or context notes.
    """

    expense_ratio: Optional[Decimal] = None
    advisory_fee_annual: Optional[Decimal] = None
    exit_cost_pct: Optional[Decimal] = None
    entry_cost_pct: Optional[Decimal] = None
    other_one_time: Optional[Decimal] = None
    other_recurring: Optional[Decimal] = None
    notes: Optional[str] = None

    @field_validator("expense_ratio")
    @classmethod
    def _expense_ratio_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"expense_ratio must be >= 0 when provided, got {v}.")
        return v

    @field_validator("advisory_fee_annual")
    @classmethod
    def _advisory_fee_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"advisory_fee_annual must be >= 0 when provided, got {v}.")
        return v

    @field_validator("exit_cost_pct")
    @classmethod
    def _exit_cost_pct_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"exit_cost_pct must be >= 0 when provided, got {v}.")
        return v

    @field_validator("entry_cost_pct")
    @classmethod
    def _entry_cost_pct_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"entry_cost_pct must be >= 0 when provided, got {v}.")
        return v

    @field_validator("other_one_time")
    @classmethod
    def _other_one_time_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"other_one_time must be >= 0 when provided, got {v}.")
        return v

    @field_validator("other_recurring")
    @classmethod
    def _other_recurring_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"other_recurring must be >= 0 when provided, got {v}.")
        return v


class Investment(BaseModel):
    """An investment product (fund, ETF, annuity, etc.).

    Fields
    ------
    product_id:      Unique identifier.
    label:           Human-readable name.
    ticker:          Ticker symbol, if applicable.
    fees:            Fee structure.
    annuity_terms:   Populated only for annuity products.
    notes:           Unresolved items or context.
    """

    product_id: str
    label: str
    ticker: Optional[str] = None
    fees: FeeStructure = Field(default_factory=FeeStructure)
    annuity_terms: Optional[AnnuityTerms] = None
    notes: Optional[str] = None
