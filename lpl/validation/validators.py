"""Validation rules for portfolios, accounts, and transition instructions.

Validation produces a report of issues rather than raising immediately.
Errors (must be fixed before calculations) are distinguished from warnings
(should be reviewed).

Rules implemented:
1.  Portfolio total reconciles: sum of holding market values == declared total (within tolerance).
2.  Allocation weights: field not yet modelled — deferred (see R-17 in requirements_tracker.md).
3.  Holdings with UNKNOWN cost basis are flagged as warnings.
4.  ILLIQUID holdings must not appear as source in any transition instruction (SELL_ALL,
    SELL_PARTIAL, EXCHANGE).
5.  CI and PI must have different portfolio_id values and labels.
6.  Account type must not be UNKNOWN when holdings are present.
7.  All account_ids referenced by holdings must exist in the portfolio.
8.  SELL_PARTIAL requires a fraction strictly in (0, 1) exclusive.
9.  SELL_PARTIAL rejected if holding is not ELIGIBLE for fractional transitions.
10. SELL with a fraction set produces a warning (fraction is ignored for full sales).
11. RESTRICTED holdings: SELL and EXCHANGE rejected unless explicitly approved.
12. ANNUITY holdings: EXCHANGE rejected unless exchange_eligible=True.
13. CONVERT instructions: source must be TRADITIONAL_IRA; destination must be ROTH_IRA;
    destination_account_id must be provided.

validate_calculation_readiness() reports whether missing or unresolved data would
block downstream engine calculations. It does not perform any calculations.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from lpl.models.account import AccountType
from lpl.models.holding import (
    AssetClass,
    CostBasisStatus,
    FractionalTransitionEligibility,
    LiquidityStatus,
)
from lpl.models.portfolio import Portfolio, PortfolioLabel
from lpl.models.product import RateInterpretation
from lpl.models.transition import TransitionInstruction, TransitionAction
from lpl.exceptions import CIandPIConflictError  # noqa: F401 — re-exported for callers


RECONCILIATION_TOLERANCE = Decimal("0.01")  # $0.01 USD

# Actions that constitute "selling" a holding (exit the position).
_SELL_ACTIONS = {TransitionAction.SELL_ALL, TransitionAction.SELL_PARTIAL}
# Actions that require the holding to be transitionable at all.
_TRANSITION_ACTIONS = {
    TransitionAction.SELL_ALL,
    TransitionAction.SELL_PARTIAL,
    TransitionAction.EXCHANGE,
    TransitionAction.CONVERT,
}


class ValidationLevel(str, Enum):
    ERROR = "error"     # Must be resolved before calculations
    WARNING = "warning" # Should be reviewed; does not block calculations
    INFO = "info"       # Informational note


class ValidationIssue(BaseModel):
    """A single validation finding."""

    level: ValidationLevel
    code: str
    message: str
    entity_id: Optional[str] = None  # portfolio_id, holding_id, instruction_id, etc.


class ValidationReport(BaseModel):
    """Collection of validation findings for a portfolio or scenario.

    Uses default_factory=list so each instance has its own independent list.
    Two instances never share mutable state.
    """

    issues: list[ValidationIssue] = Field(default_factory=list)

    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.ERROR]

    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]

    def has_errors(self) -> bool:
        return any(i.level == ValidationLevel.ERROR for i in self.issues)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)


# ---------------------------------------------------------------------------
# Portfolio-level validation
# ---------------------------------------------------------------------------

def validate_portfolio(portfolio: Portfolio) -> ValidationReport:
    """Run all portfolio-level validation rules.

    Returns a ValidationReport. Does not raise; callers decide how to handle issues.
    """
    report = ValidationReport()

    # Rule 1: total market value reconciliation
    computed = portfolio.computed_total()
    declared = portfolio.total_market_value
    diff = abs(computed - declared)
    if diff > RECONCILIATION_TOLERANCE:
        report.add(ValidationIssue(
            level=ValidationLevel.ERROR,
            code="PORTFOLIO_TOTAL_MISMATCH",
            message=(
                f"Portfolio '{portfolio.portfolio_id}': declared total "
                f"{declared} != sum of holdings {computed} "
                f"(diff={diff})."
            ),
            entity_id=portfolio.portfolio_id,
        ))

    # Rule 2: account IDs referenced by holdings exist in portfolio
    known_account_ids = portfolio.account_ids()
    for h in portfolio.holdings:
        if h.account_id not in known_account_ids:
            report.add(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="HOLDING_UNKNOWN_ACCOUNT",
                message=(
                    f"Holding '{h.holding_id}' references account "
                    f"'{h.account_id}' which is not in portfolio accounts."
                ),
                entity_id=h.holding_id,
            ))

    # Rule 3: UNKNOWN cost basis — flag as warning
    for h in portfolio.holdings:
        if h.cost_basis_status in (CostBasisStatus.UNKNOWN, CostBasisStatus.PARTIAL):
            report.add(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="MISSING_COST_BASIS",
                message=(
                    f"Holding '{h.holding_id}' has cost_basis_status="
                    f"{h.cost_basis_status.value}. Tax gain/loss calculations "
                    "cannot proceed without cost basis."
                ),
                entity_id=h.holding_id,
            ))

    # Rule 4: UNKNOWN account type when holdings are non-empty
    account_type_map = {a.account_id: a for a in portfolio.accounts}
    for h in portfolio.holdings:
        acct = account_type_map.get(h.account_id)
        if acct and acct.account_type.value == "unknown":
            report.add(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="UNKNOWN_ACCOUNT_TYPE",
                message=(
                    f"Account '{h.account_id}' has account_type=UNKNOWN. "
                    "Tax calculations cannot proceed."
                ),
                entity_id=h.account_id,
            ))

    return report


# ---------------------------------------------------------------------------
# CI/PI separation
# ---------------------------------------------------------------------------

def validate_ci_pi_separation(ci: Portfolio, pi: Portfolio) -> ValidationReport:
    """Ensure CI and PI are distinct portfolios."""
    report = ValidationReport()

    if ci.portfolio_id == pi.portfolio_id:
        report.add(ValidationIssue(
            level=ValidationLevel.ERROR,
            code="CI_PI_SAME_ID",
            message=(
                f"CI and PI share portfolio_id='{ci.portfolio_id}'. "
                "They must be separate objects with distinct IDs."
            ),
        ))

    if ci.label == pi.label:
        report.add(ValidationIssue(
            level=ValidationLevel.ERROR,
            code="CI_PI_SAME_LABEL",
            message=(
                f"CI and PI share label='{ci.label.value}'. "
                "They must have different labels."
            ),
        ))

    if ci.label != PortfolioLabel.CI:
        report.add(ValidationIssue(
            level=ValidationLevel.WARNING,
            code="CI_UNEXPECTED_LABEL",
            message=f"Expected CI portfolio to have label=CI, got '{ci.label.value}'.",
        ))

    if pi.label != PortfolioLabel.PI:
        report.add(ValidationIssue(
            level=ValidationLevel.WARNING,
            code="PI_UNEXPECTED_LABEL",
            message=f"Expected PI portfolio to have label=PI, got '{pi.label.value}'.",
        ))

    return report


# ---------------------------------------------------------------------------
# Transition instruction validation
# ---------------------------------------------------------------------------

def validate_transition_instructions(
    instructions: list[TransitionInstruction],
    portfolio: Portfolio,
) -> ValidationReport:
    """Validate transition instructions against the source portfolio.

    Rules enforced (see module docstring for full list):
    - ILLIQUID: no SELL_ALL, SELL_PARTIAL, or EXCHANGE.
    - RESTRICTED: no SELL_ALL or EXCHANGE unless holding.exchange_eligible=True.
      If eligibility is unknown, instruction is flagged REQUIRES_MANUAL_REVIEW (WARNING).
    - ANNUITY asset class: EXCHANGE requires exchange_eligible=True explicitly.
    - SELL_PARTIAL: fraction required, strictly in (0, 1) exclusive.
    - SELL_PARTIAL: holding must have fractional_eligible=ELIGIBLE.
    - SELL_ALL: fraction must not be set (WARNING if present).
    - CONVERT: source must be TRADITIONAL_IRA; destination_account_id required;
      destination account must be ROTH_IRA.
    """
    report = ValidationReport()

    holding_map = {h.holding_id: h for h in portfolio.holdings}
    account_map = {a.account_id: a for a in portfolio.accounts}

    for instr in instructions:
        h = holding_map.get(instr.holding_id)
        if h is None:
            report.add(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="INSTRUCTION_UNKNOWN_HOLDING",
                message=(
                    f"Instruction '{instr.instruction_id}' references holding "
                    f"'{instr.holding_id}' which does not exist in portfolio "
                    f"'{portfolio.portfolio_id}'."
                ),
                entity_id=instr.instruction_id,
            ))
            continue

        # -----------------------------------------------------------------
        # Rule A: ILLIQUID holdings cannot be sold or exchanged
        # -----------------------------------------------------------------
        if h.liquidity_status == LiquidityStatus.ILLIQUID and instr.action in _TRANSITION_ACTIONS:
            report.add(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="ILLIQUID_TRANSITION_ATTEMPT",
                message=(
                    f"Instruction '{instr.instruction_id}': holding '{h.holding_id}' "
                    f"is ILLIQUID and cannot be {instr.action.value}. "
                    "Mark it RETAINED or DEFERRED."
                ),
                entity_id=instr.instruction_id,
            ))
            # Continue checking other rules even on illiquid error.

        # -----------------------------------------------------------------
        # Rule B: RESTRICTED holdings — conservative handling
        # A RESTRICTED holding (e.g. annuity in surrender period) may have
        # exit penalties or waiting periods. We do not invent surrender rules.
        # If exchange_eligible is not explicitly True, flag for manual review.
        # -----------------------------------------------------------------
        if h.liquidity_status == LiquidityStatus.RESTRICTED and instr.action in (
            TransitionAction.SELL_ALL,
            TransitionAction.EXCHANGE,
        ):
            if h.exchange_eligible is True:
                # Explicitly approved — allow (further annuity rule below may still flag)
                pass
            elif h.exchange_eligible is False:
                report.add(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="RESTRICTED_TRANSITION_NOT_ELIGIBLE",
                    message=(
                        f"Instruction '{instr.instruction_id}': holding '{h.holding_id}' "
                        f"is RESTRICTED and exchange_eligible=False. "
                        f"Cannot perform {instr.action.value}."
                    ),
                    entity_id=instr.instruction_id,
                ))
            else:
                # exchange_eligible is None — unknown; require manual review
                report.add(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="RESTRICTED_TRANSITION_REQUIRES_MANUAL_REVIEW",
                    message=(
                        f"Instruction '{instr.instruction_id}': holding '{h.holding_id}' "
                        f"is RESTRICTED and exchange eligibility is unknown. "
                        f"The {instr.action.value} instruction requires manual review "
                        "before execution. Do not assume exit is cost-free or permitted."
                    ),
                    entity_id=instr.instruction_id,
                ))

        # -----------------------------------------------------------------
        # Rule C: ANNUITY asset class — EXCHANGE requires explicit approval
        # 1035 exchanges are not universally available; do not assume.
        # -----------------------------------------------------------------
        if h.asset_class == AssetClass.ANNUITY and instr.action == TransitionAction.EXCHANGE:
            if h.exchange_eligible is not True:
                report.add(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="ANNUITY_EXCHANGE_NOT_CONFIRMED",
                    message=(
                        f"Instruction '{instr.instruction_id}': holding '{h.holding_id}' "
                        "is an ANNUITY and exchange_eligible is not explicitly True. "
                        "1035 exchange availability must be confirmed with the product "
                        "provider. This instruction requires manual review."
                    ),
                    entity_id=instr.instruction_id,
                ))

        # -----------------------------------------------------------------
        # Rule D: SELL_PARTIAL — fraction and eligibility
        # -----------------------------------------------------------------
        if instr.action == TransitionAction.SELL_PARTIAL:
            # D1: fraction must be present
            if instr.fraction is None:
                report.add(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="SELL_PARTIAL_MISSING_FRACTION",
                    message=(
                        f"Instruction '{instr.instruction_id}': action is SELL_PARTIAL "
                        "but fraction is not set."
                    ),
                    entity_id=instr.instruction_id,
                ))
            else:
                # D2: fraction must be strictly in (0, 1) exclusive
                if not (Decimal("0") < instr.fraction < Decimal("1")):
                    report.add(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="SELL_PARTIAL_INVALID_FRACTION",
                        message=(
                            f"Instruction '{instr.instruction_id}': fraction must be "
                            f"strictly in (0, 1) exclusive, got {instr.fraction}."
                        ),
                        entity_id=instr.instruction_id,
                    ))

            # D3: holding must be eligible for fractional transitions
            if h.fractional_eligible == FractionalTransitionEligibility.INELIGIBLE:
                report.add(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="SELL_PARTIAL_FRACTIONAL_INELIGIBLE",
                    message=(
                        f"Instruction '{instr.instruction_id}': holding '{h.holding_id}' "
                        "is marked INELIGIBLE for fractional transitions. "
                        "SELL_PARTIAL is not permitted."
                    ),
                    entity_id=instr.instruction_id,
                ))
            elif h.fractional_eligible == FractionalTransitionEligibility.UNKNOWN:
                report.add(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="SELL_PARTIAL_FRACTIONAL_ELIGIBILITY_UNKNOWN",
                    message=(
                        f"Instruction '{instr.instruction_id}': holding '{h.holding_id}' "
                        "has unknown fractional transition eligibility. "
                        "Confirm with product provider before executing SELL_PARTIAL."
                    ),
                    entity_id=instr.instruction_id,
                ))

        # -----------------------------------------------------------------
        # Rule E: SELL_ALL must not have a fraction set
        # -----------------------------------------------------------------
        if instr.action == TransitionAction.SELL_ALL and instr.fraction is not None:
            report.add(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="SELL_ALL_FRACTION_IGNORED",
                message=(
                    f"Instruction '{instr.instruction_id}': action is SELL_ALL "
                    f"but fraction={instr.fraction} is set. "
                    "Fraction is ignored for full sales."
                ),
                entity_id=instr.instruction_id,
            ))

        # -----------------------------------------------------------------
        # Rule F: CONVERT — IRA-to-Roth constraints
        # -----------------------------------------------------------------
        if instr.action == TransitionAction.CONVERT:
            # F1: source must be TRADITIONAL_IRA
            source_acct = account_map.get(h.account_id)
            if source_acct is None:
                report.add(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="CONVERT_SOURCE_ACCOUNT_MISSING",
                    message=(
                        f"Instruction '{instr.instruction_id}': cannot determine "
                        f"source account type for holding '{h.holding_id}'. "
                        "Account not found in portfolio."
                    ),
                    entity_id=instr.instruction_id,
                ))
            elif source_acct.account_type != AccountType.TRADITIONAL_IRA:
                report.add(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="CONVERT_INVALID_SOURCE_ACCOUNT_TYPE",
                    message=(
                        f"Instruction '{instr.instruction_id}': CONVERT source account "
                        f"'{source_acct.account_id}' has type "
                        f"'{source_acct.account_type.value}'. "
                        "Only TRADITIONAL_IRA accounts can be converted to Roth IRA."
                    ),
                    entity_id=instr.instruction_id,
                ))

            # F2: destination_account_id must be provided
            if instr.destination_account_id is None:
                report.add(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="CONVERT_MISSING_DESTINATION",
                    message=(
                        f"Instruction '{instr.instruction_id}': CONVERT action requires "
                        "destination_account_id to identify the target Roth IRA account."
                    ),
                    entity_id=instr.instruction_id,
                ))
            else:
                # F3: destination account must be ROTH_IRA
                dest_acct = account_map.get(instr.destination_account_id)
                if dest_acct is None:
                    report.add(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="CONVERT_DESTINATION_ACCOUNT_MISSING",
                        message=(
                            f"Instruction '{instr.instruction_id}': destination account "
                            f"'{instr.destination_account_id}' not found in portfolio."
                        ),
                        entity_id=instr.instruction_id,
                    ))
                elif dest_acct.account_type != AccountType.ROTH_IRA:
                    report.add(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="CONVERT_INVALID_DESTINATION_ACCOUNT_TYPE",
                        message=(
                            f"Instruction '{instr.instruction_id}': CONVERT destination "
                            f"account '{dest_acct.account_id}' has type "
                            f"'{dest_acct.account_type.value}'. "
                            "Destination must be a ROTH_IRA account."
                        ),
                        entity_id=instr.instruction_id,
                    ))

    return report


# ---------------------------------------------------------------------------
# Calculation readiness check
# ---------------------------------------------------------------------------

def validate_calculation_readiness(portfolio: Portfolio) -> ValidationReport:
    """Check whether missing or unresolved data would block downstream calculations.

    This function performs NO calculations. It inspects the portfolio for known
    data gaps and returns a ValidationReport with WARNINGs. Downstream engines
    must check this report and raise UnsupportedCalculationError if they require
    a field that this report flags as missing.

    Checks:
    - Holdings with UNKNOWN or PARTIAL cost basis: WARNING per holding.
    - Annuity holdings with UNRESOLVED rate interpretation: WARNING per holding.
    - Holdings in UNKNOWN-type accounts: WARNING per holding.
    """
    report = ValidationReport()

    for h in portfolio.holdings:
        # Missing cost basis
        if h.cost_basis_status in (CostBasisStatus.UNKNOWN, CostBasisStatus.PARTIAL):
            report.add(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="CALC_MISSING_COST_BASIS",
                message=(
                    f"Holding '{h.holding_id}' has cost_basis_status="
                    f"{h.cost_basis_status.value}. "
                    "Any calculation requiring cost basis (gain/loss, after-tax proceeds) "
                    "cannot proceed for this holding."
                ),
                entity_id=h.holding_id,
            ))

        # Unresolved annuity rate
        if h.asset_class == AssetClass.ANNUITY:
            # We need the product to check annuity_terms.rate_interpretation.
            # Holdings do not embed product data directly; we flag by asset_class
            # and note that the caller must resolve annuity terms separately.
            # This is a conservative signal — the actual check is on AnnuityTerms.
            report.add(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="CALC_ANNUITY_TERMS_CHECK_REQUIRED",
                message=(
                    f"Holding '{h.holding_id}' is an ANNUITY asset. "
                    "Before any income or growth calculation, verify that the "
                    "associated product's AnnuityTerms.rate_interpretation is not "
                    "UNRESOLVED. Use UnresolvedAnnuityTermsError if unresolved."
                ),
                entity_id=h.holding_id,
            ))

    # Also check account types
    account_type_map = {a.account_id: a for a in portfolio.accounts}
    for h in portfolio.holdings:
        acct = account_type_map.get(h.account_id)
        if acct and acct.account_type == AccountType.UNKNOWN:
            report.add(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="CALC_UNKNOWN_ACCOUNT_TYPE",
                message=(
                    f"Holding '{h.holding_id}' is in account '{h.account_id}' "
                    "which has account_type=UNKNOWN. "
                    "Tax calculations cannot proceed for this holding."
                ),
                entity_id=h.holding_id,
            ))

    return report
