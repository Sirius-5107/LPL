"""Decision engine contract.

The decision engine synthesises outputs from all other engines into a
recommendation. It must:
- Never invent or override financial figures.
- Produce an auditable, explainable recommendation.
- Distinguish between supported and unsupported sub-recommendations.

This module contains Protocol definitions only — no implementations.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional, Protocol

from lpl.models.scenario import Scenario
from lpl.models.assumptions import AssumptionsRegister


class RecommendationOutcome(str, Enum):
    """High-level recommendation outcome."""

    RETAIN_CI = "retain_ci"
    TRANSITION_TO_PI = "transition_to_pi"
    PARTIAL_TRANSITION = "partial_transition"
    STAGED_TRANSITION = "staged_transition"
    TRANSITION_TO_RI = "transition_to_ri"
    INSUFFICIENT_DATA = "insufficient_data"  # Too many unresolved inputs
    REVIEW_REQUIRED = "review_required"


class DecisionEngineInput(Protocol):
    """Input to the decision engine — all computed engine outputs plus the scenario."""

    @property
    def scenario(self) -> Scenario: ...

    @property
    def tax_net_cost(self) -> Optional[Decimal]:
        """Net after-tax transition cost across all holdings. None if unsupported."""
        ...

    @property
    def one_time_cost_total(self) -> Optional[Decimal]:
        """Total one-time transition cost. None if unsupported."""
        ...

    @property
    def annual_cost_delta(self) -> Optional[Decimal]:
        """Annual recurring cost change (PI - CI). None if unsupported."""
        ...

    @property
    def ci_retirement_age_of_depletion(self) -> Optional[int]:
        """Age at which CI depletes. None if projection unsupported."""
        ...

    @property
    def pi_retirement_age_of_depletion(self) -> Optional[int]:
        """Age at which PI depletes. None if projection unsupported."""
        ...

    @property
    def assumptions(self) -> AssumptionsRegister: ...


class DecisionEngineOutput(Protocol):
    """Output from the decision engine."""

    @property
    def outcome(self) -> RecommendationOutcome: ...

    @property
    def rationale(self) -> str:
        """Human-readable explanation of the recommendation."""
        ...

    @property
    def supporting_metrics(self) -> dict:
        """Key metrics used in the decision. All values are pass-through — not invented."""
        ...

    @property
    def unresolved_items(self) -> list[str]:
        """List of unresolved assumptions or missing data that limited the analysis."""
        ...

    @property
    def is_complete(self) -> bool:
        """True if all required inputs were available. False = INSUFFICIENT_DATA."""
        ...


class DecisionEngine(Protocol):
    """Interface for the quantitative decision engine."""

    def recommend(self, input: DecisionEngineInput) -> DecisionEngineOutput:
        """Produce a recommendation from synthesised engine outputs."""
        ...
