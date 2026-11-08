"""Domain exceptions for the LPL decision-support system.

All exceptions are explicit and descriptive. The system must never silently
swallow missing data or approximate unsupported calculations.
"""


class LPLBaseError(Exception):
    """Base class for all LPL domain errors."""


class MissingCostBasisError(LPLBaseError, ValueError):
    """Raised when a tax-sensitive calculation requires cost basis that was not provided.

    Cost basis must never silently default to zero. Any code path that needs
    cost basis must check ``holding.cost_basis_status`` before using the value.
    """

    def __init__(self, holding_id: str, context: str = "") -> None:
        msg = (
            f"Cost basis is unknown for holding '{holding_id}'. "
            "It must not be assumed to be zero. "
            f"Context: {context}" if context else
            f"Cost basis is unknown for holding '{holding_id}'. "
            "It must not be assumed to be zero."
        )
        super().__init__(msg)
        self.holding_id = holding_id


class IlliquidAssetTransitionError(LPLBaseError, ValueError):
    """Raised when an illiquid asset is included in a transition instruction.

    Illiquid assets cannot be automatically sold or transitioned. Any transition
    plan must explicitly exclude them or mark them as RETAINED.
    """

    def __init__(self, holding_id: str) -> None:
        super().__init__(
            f"Holding '{holding_id}' is ILLIQUID and cannot be included in a "
            "transition instruction. Mark it as RETAINED or remove it."
        )
        self.holding_id = holding_id


class UnsupportedCalculationError(LPLBaseError, NotImplementedError):
    """Raised when a required calculation cannot be completed due to missing inputs.

    Examples: tax rate not provided, annuity terms unresolved, conversion amount unknown.
    The calculation must be flagged rather than approximated silently.
    """

    def __init__(self, calculation: str, missing: str) -> None:
        super().__init__(
            f"Cannot perform '{calculation}': required input missing — {missing}. "
            "Provide the missing data or mark the output as UNRESOLVED."
        )
        self.calculation = calculation
        self.missing = missing


class UnresolvedAnnuityTermsError(LPLBaseError, ValueError):
    """Raised when annuity rate interpretation is used before it is resolved.

    'Payout rate', 'guaranteed interest rate', and 'withdrawal rate' are distinct
    concepts. Until the dossier term is clarified, no rate-dependent calculation
    should proceed.
    """

    def __init__(self, annuity_id: str, description: str) -> None:
        super().__init__(
            f"Annuity '{annuity_id}' has unresolved rate interpretation: "
            f"'{description}'. Resolve whether this is a payout rate, guaranteed "
            "interest rate, or withdrawal rate before computing income projections."
        )
        self.annuity_id = annuity_id


class PortfolioReconciliationError(LPLBaseError, ValueError):
    """Raised when holding values do not sum to the declared portfolio total."""

    def __init__(self, portfolio_id: str, declared: object, computed: object) -> None:
        super().__init__(
            f"Portfolio '{portfolio_id}' reconciliation failed: "
            f"declared total={declared}, sum of holdings={computed}."
        )
        self.portfolio_id = portfolio_id


class CIandPIConflictError(LPLBaseError, ValueError):
    """Raised when CI and PI portfolios share an ID or label."""
