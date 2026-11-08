"""Retirement engine contract.

Models retirement income projections and sustainability.
All projections are nominal unless real is explicitly requested.
Retirement ages span 60–90 per the problem statement.

This module contains Protocol definitions only — no implementations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol

from lpl.models.client import Client
from lpl.models.portfolio import Portfolio
from lpl.models.assumptions import AssumptionsRegister


class RetirementEngineInput(Protocol):
    """Input to the retirement projection engine."""

    @property
    def client(self) -> Client:
        """Client with demographic and goal information."""
        ...

    @property
    def portfolio(self) -> Portfolio:
        """Portfolio to project (CI or PI)."""
        ...

    @property
    def projection_to_age(self) -> int:
        """Age at which to end the projection (e.g. 90)."""
        ...

    @property
    def expected_annual_return(self) -> Optional[Decimal]:
        """Expected nominal annual return. None = not provided."""
        ...

    @property
    def inflation_rate_annual(self) -> Optional[Decimal]:
        """Annual inflation assumption. None = not provided."""
        ...

    @property
    def assumptions(self) -> AssumptionsRegister:
        """Assumptions register for this projection."""
        ...


class AnnualProjection(Protocol):
    """A single year's projection snapshot."""

    @property
    def age(self) -> int: ...

    @property
    def portfolio_value_nominal(self) -> Decimal:
        """Projected portfolio value in nominal USD."""
        ...

    @property
    def portfolio_value_real(self) -> Optional[Decimal]:
        """Projected portfolio value in real USD. None if inflation not provided."""
        ...

    @property
    def income_distributed_nominal(self) -> Decimal:
        """Income distributed this year in nominal USD."""
        ...

    @property
    def is_solvent(self) -> bool:
        """True if portfolio value > 0 at start of this year."""
        ...


class RetirementEngineOutput(Protocol):
    """Output from the retirement projection engine."""

    @property
    def projections(self) -> list[AnnualProjection]:
        """Year-by-year projections from current age to projection_to_age."""
        ...

    @property
    def age_of_depletion(self) -> Optional[int]:
        """Age at which portfolio is projected to reach zero. None if sustainable."""
        ...

    @property
    def probability_of_success(self) -> Optional[Decimal]:
        """Monte Carlo success rate if stochastic method was used. None for deterministic."""
        ...

    @property
    def is_supported(self) -> bool:
        """False if required inputs were missing."""
        ...

    @property
    def unsupported_reason(self) -> Optional[str]: ...


class RetirementEngine(Protocol):
    """Interface for the retirement projection engine."""

    def project(self, input: RetirementEngineInput) -> RetirementEngineOutput:
        """Run a retirement projection."""
        ...
