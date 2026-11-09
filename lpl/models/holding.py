"""Holding model — a single position within an account.

Design constraints enforced here:
- Cost basis is Optional[Decimal]. Accessing it without checking status raises
  MissingCostBasisError in business logic (not here — models are pure data).
- Liquidity status is explicit and drives transition eligibility checks.
- Nominal vs real values: market_value is always nominal. If a real (inflation-
  adjusted) value is needed, it must be computed and stored separately.
- Gross vs net performance: a Holding does not store performance; that belongs
  in the PerformanceEngine output. Expense ratio is stored here as a cost input.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AssetClass(str, Enum):
    """Broad asset-class taxonomy."""

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    REAL_ESTATE = "real_estate"
    ALTERNATIVES = "alternatives"
    ANNUITY = "annuity"
    CASH = "cash"
    UNKNOWN = "unknown"


class LiquidityStatus(str, Enum):
    """Liquidity classification of a holding.

    ILLIQUID holdings must not appear as a source in any TransitionInstruction.
    RESTRICTED holdings (e.g., annuities in surrender period) may have partial
    exit costs or waiting periods that must be explicitly modelled.
    """

    LIQUID = "liquid"
    PARTIALLY_LIQUID = "partially_liquid"
    RESTRICTED = "restricted"       # e.g. annuity surrender period
    ILLIQUID = "illiquid"


class CostBasisStatus(str, Enum):
    """Tracks whether cost basis is available.

    KNOWN:        cost_basis field is populated and reliable.
    UNKNOWN:      cost basis was not provided; must not be assumed zero.
    INAPPLICABLE: cost basis concept does not apply (e.g., Roth conversion
                  already taxed; some annuity contracts).
    PARTIAL:      some lots have known basis, others do not.
    """

    KNOWN = "known"
    UNKNOWN = "unknown"
    INAPPLICABLE = "inapplicable"
    PARTIAL = "partial"


class FractionalTransitionEligibility(str, Enum):
    """Whether the holding can be partially (fractionally) transitioned."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"


class Holding(BaseModel):
    """A single position within an account.

    Fields
    ------
    holding_id:            Unique identifier.
    account_id:            Parent account this holding belongs to.
    label:                 Human-readable name, e.g. "S&P 500 mutual fund".
    asset_class:           Broad classification.
    market_value:          Current nominal market value in USD (Decimal required).
    cost_basis:            Original purchase cost in USD. None if unknown — NEVER zero by default.
    cost_basis_status:     Explicit status of cost_basis field.
    liquidity_status:      Liquidity classification.
    fractional_eligible:   Whether partial transition is possible.
    expense_ratio:         Annual fund expense ratio as a decimal (e.g. 0.0075 = 0.75%).
    exit_cost_pct:         One-time exit cost as a decimal (e.g. 0.01 = 1%).
    notes:                 Unresolved items or context.
    sub_holdings:          Nested holdings for composite positions (e.g. alternatives sleeve).
    """

    holding_id: str
    account_id: str
    label: str
    asset_class: AssetClass = AssetClass.UNKNOWN
    market_value: Decimal = Field(..., description="Nominal USD market value.")
    cost_basis: Optional[Decimal] = Field(
        None,
        description=(
            "Original cost in USD. None means UNKNOWN — not zero. "
            "Check cost_basis_status before using this field."
        ),
    )
    cost_basis_status: CostBasisStatus = CostBasisStatus.UNKNOWN
    liquidity_status: LiquidityStatus = LiquidityStatus.LIQUID
    fractional_eligible: FractionalTransitionEligibility = FractionalTransitionEligibility.UNKNOWN
    exchange_eligible: Optional[bool] = Field(
        None,
        description=(
            "Whether this holding is explicitly approved for an in-kind or 1035 exchange. "
            "None means unknown — do not assume eligible. "
            "Annuity exchanges must not be assumed available without explicit approval. "
            "This field does NOT authorize a SELL_ALL or SELL_PARTIAL — use sale_eligible for that."
        ),
    )
    sale_eligible: Optional[bool] = Field(
        None,
        description=(
            "Whether this holding is explicitly approved for an ordinary sale (SELL_ALL or SELL_PARTIAL). "
            "Applies to RESTRICTED holdings only; LIQUID holdings do not require this flag. "
            "None means unknown — conservative validation will block or flag for manual review. "
            "Must never be inferred from exchange_eligible; they are entirely separate approvals."
        ),
    )
    expense_ratio: Optional[Decimal] = Field(
        None, description="Annual expense ratio as decimal fraction."
    )
    exit_cost_pct: Optional[Decimal] = Field(
        None, description="One-time exit cost as decimal fraction."
    )
    notes: Optional[str] = None
    sub_holdings: list["Holding"] = Field(default_factory=list)

    @field_validator("market_value")
    @classmethod
    def _market_value_non_negative(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError(f"market_value must be >= 0, got {v}.")
        return v

    @field_validator("cost_basis")
    @classmethod
    def _cost_basis_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"cost_basis must be >= 0 when provided, got {v}.")
        return v

    @field_validator("expense_ratio")
    @classmethod
    def _expense_ratio_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"expense_ratio must be >= 0 when provided, got {v}.")
        return v

    @field_validator("exit_cost_pct")
    @classmethod
    def _exit_cost_pct_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError(f"exit_cost_pct must be >= 0 when provided, got {v}.")
        return v

    @model_validator(mode="after")
    def _cost_basis_consistency(self) -> "Holding":
        """Ensure cost_basis and cost_basis_status are consistent."""
        if self.cost_basis is not None and self.cost_basis_status == CostBasisStatus.UNKNOWN:
            raise ValueError(
                f"Holding '{self.holding_id}': cost_basis is provided but "
                "cost_basis_status is UNKNOWN. Set status to KNOWN."
            )
        if self.cost_basis is None and self.cost_basis_status == CostBasisStatus.KNOWN:
            raise ValueError(
                f"Holding '{self.holding_id}': cost_basis_status is KNOWN but "
                "cost_basis is None. Provide the value or change status."
            )
        return self
