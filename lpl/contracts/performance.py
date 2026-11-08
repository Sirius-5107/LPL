"""Performance engine contract.

Gross vs net performance must always be distinguishable.
Nominal vs real returns must always be distinguishable.
Historical performance is not a guarantee of future results.

This module contains Protocol definitions only — no implementations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol

from lpl.models.holding import Holding
from lpl.models.assumptions import AssumptionsRegister


class PerformanceEngineInput(Protocol):
    """Input to the performance analysis engine."""

    @property
    def holding(self) -> Holding:
        """The holding to analyse."""
        ...

    @property
    def lookback_years(self) -> int:
        """Number of years of historical data to include."""
        ...

    @property
    def inflation_rate_annual(self) -> Optional[Decimal]:
        """Annual inflation rate assumption for real return conversion. None = not provided."""
        ...

    @property
    def assumptions(self) -> AssumptionsRegister:
        """Assumptions register for this calculation."""
        ...


class PerformanceEngineOutput(Protocol):
    """Output from the performance analysis engine.

    Gross and net returns, and nominal and real returns, are always separate fields.
    """

    @property
    def annualised_gross_return_nominal(self) -> Optional[Decimal]:
        """Annualised gross return (before fees), nominal. None if not computable."""
        ...

    @property
    def annualised_net_return_nominal(self) -> Optional[Decimal]:
        """Annualised net return (after expense ratio), nominal."""
        ...

    @property
    def annualised_net_return_real(self) -> Optional[Decimal]:
        """Annualised net return adjusted for inflation. None if inflation_rate not provided."""
        ...

    @property
    def max_drawdown(self) -> Optional[Decimal]:
        """Maximum peak-to-trough drawdown over the lookback period."""
        ...

    @property
    def volatility_annual(self) -> Optional[Decimal]:
        """Annualised volatility (standard deviation of returns)."""
        ...

    @property
    def sharpe_ratio(self) -> Optional[Decimal]:
        """Sharpe ratio. None if risk-free rate not provided."""
        ...

    @property
    def data_source(self) -> Optional[str]:
        """Source of historical return data."""
        ...

    @property
    def is_supported(self) -> bool:
        """False if historical data was unavailable or incomplete."""
        ...


class PerformanceEngine(Protocol):
    """Interface for the performance analysis engine."""

    def analyse(self, input: PerformanceEngineInput) -> PerformanceEngineOutput:
        """Compute historical performance metrics for a holding."""
        ...
