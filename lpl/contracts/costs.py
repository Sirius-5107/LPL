"""Cost engine contract.

Separates one-time transition costs from recurring (annual) costs.
Both are nominal USD unless explicitly noted otherwise.

This module contains Protocol definitions only — no implementations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol

from lpl.models.holding import Holding
from lpl.models.product import FeeStructure
from lpl.models.transition import TransitionInstruction


class CostEngineInput(Protocol):
    """Input to the cost calculation engine."""

    @property
    def holding(self) -> Holding:
        """The holding being transitioned."""
        ...

    @property
    def instruction(self) -> TransitionInstruction:
        """The transition instruction."""
        ...

    @property
    def current_fee_structure(self) -> FeeStructure:
        """Fee structure of the current product."""
        ...

    @property
    def proposed_fee_structure(self) -> Optional[FeeStructure]:
        """Fee structure of the proposed product. None if retaining."""
        ...


class CostEngineOutput(Protocol):
    """Output from the cost calculation engine.

    One-time and recurring costs are ALWAYS separate.
    """

    @property
    def one_time_exit_cost(self) -> Optional[Decimal]:
        """One-time cost to exit the current holding (nominal USD)."""
        ...

    @property
    def one_time_entry_cost(self) -> Optional[Decimal]:
        """One-time cost to enter the proposed holding (nominal USD)."""
        ...

    @property
    def total_one_time_cost(self) -> Optional[Decimal]:
        """Sum of all one-time costs (nominal USD)."""
        ...

    @property
    def current_annual_recurring_cost(self) -> Optional[Decimal]:
        """Current product's annual recurring cost on this holding (nominal USD)."""
        ...

    @property
    def proposed_annual_recurring_cost(self) -> Optional[Decimal]:
        """Proposed product's annual recurring cost (nominal USD). None if retaining."""
        ...

    @property
    def annual_recurring_cost_delta(self) -> Optional[Decimal]:
        """proposed_annual - current_annual. Negative = cost reduction."""
        ...

    @property
    def breakeven_years(self) -> Optional[Decimal]:
        """Years to recover one-time costs via recurring cost savings. None if not computable."""
        ...


class CostEngine(Protocol):
    """Interface for the cost calculation engine."""

    def calculate(self, input: CostEngineInput) -> CostEngineOutput:
        """Calculate transition costs for a single holding instruction."""
        ...
