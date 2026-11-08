"""Portfolio model.

CI (current investment) and PI (proposed investment) must be distinct objects
with different IDs and labels. They must never be mutated into each other.

Nominal vs real values: total_market_value is always nominal USD.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from lpl.models.account import Account
from lpl.models.holding import Holding


class PortfolioLabel(str, Enum):
    """Semantic role of the portfolio in a transition analysis."""

    CI = "CI"   # Current Investment Portfolio
    PI = "PI"   # Proposed Investment Portfolio
    RI = "RI"   # Independently Recommended Portfolio


class Portfolio(BaseModel):
    """A complete investment portfolio.

    Fields
    ------
    portfolio_id:        Unique identifier. CI and PI must have different IDs.
    label:               Semantic role (CI, PI, RI).
    accounts:            All accounts in the portfolio.
    holdings:            All holdings across accounts.
    total_market_value:  Declared total nominal USD. Used for reconciliation.
    as_of_date:          Valuation date in ISO-8601 format (YYYY-MM-DD), if known.
    notes:               Unresolved items or context.
    """

    portfolio_id: str
    label: PortfolioLabel
    accounts: list[Account] = Field(default_factory=list)
    holdings: list[Holding] = Field(default_factory=list)
    total_market_value: Decimal = Field(
        ..., description="Declared total nominal USD market value."
    )
    as_of_date: Optional[str] = None
    notes: Optional[str] = None

    def computed_total(self) -> Decimal:
        """Sum of all holding market values (nominal USD)."""
        return sum((h.market_value for h in self.holdings), Decimal("0"))

    def account_ids(self) -> set[str]:
        return {a.account_id for a in self.accounts}


class PortfolioSummary(BaseModel):
    """High-level summary suitable for display or logging.

    Does not contain holding detail — computed from a Portfolio.
    """

    portfolio_id: str
    label: PortfolioLabel
    total_market_value: Decimal
    holding_count: int
    account_count: int
    unresolved_cost_basis_count: int
    illiquid_holding_count: int
    as_of_date: Optional[str] = None

    @classmethod
    def from_portfolio(cls, portfolio: Portfolio) -> "PortfolioSummary":
        from lpl.models.holding import CostBasisStatus, LiquidityStatus

        unresolved_cb = sum(
            1 for h in portfolio.holdings
            if h.cost_basis_status in (CostBasisStatus.UNKNOWN, CostBasisStatus.PARTIAL)
        )
        illiquid = sum(
            1 for h in portfolio.holdings
            if h.liquidity_status == LiquidityStatus.ILLIQUID
        )
        return cls(
            portfolio_id=portfolio.portfolio_id,
            label=portfolio.label,
            total_market_value=portfolio.total_market_value,
            holding_count=len(portfolio.holdings),
            account_count=len(portfolio.accounts),
            unresolved_cost_basis_count=unresolved_cb,
            illiquid_holding_count=illiquid,
            as_of_date=portfolio.as_of_date,
        )
