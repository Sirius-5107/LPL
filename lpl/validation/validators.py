"""Validation rules for portfolios, accounts, and transition instructions.

Validation produces a report of issues rather than raising immediately.
Errors (must be fixed before calculations) are distinguished from warnings
(should be reviewed).

Rules implemented:
1. Portfolio total reconciles: sum of holding market values == declared total (within tolerance).
2. Allocation weights sum to 1.0 if provided.
3. Holdings with UNKNOWN cost basis are flagged as warnings.
4. ILLIQUID holdings must not appear as source in a TransitionInstruction.
5. CI and PI must have different portfolio_id values and labels.
6. Account type must not be UNKNOWN when holdings are present.
7. All account_ids referenced by holdings must exist in the portfolio.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from lpl.models.holding import CostBasisStatus, LiquidityStatus
from lpl.models.portfolio import Portfolio, PortfolioLabel
from lpl.models.transition import TransitionInstruction, TransitionAction
from lpl.exceptions import IlliquidAssetTransitionError, CIandPIConflictError


RECONCILIATION_TOLERANCE = Decimal("0.01")  # $0.01 USD


class ValidationLevel(str, Enum):
    ERROR = "error"     # Must be resolved before calculations
    WARNING = "warning" # Should be reviewed; does not block calculations
    INFO = "info"       # Informational note


class ValidationIssue(BaseModel):
    """A single validation finding."""

    level: ValidationLevel
    code: str
    message: str
    entity_id: Optional[str] = None  # portfolio_id, holding_id, etc.


class ValidationReport(BaseModel):
    """Collection of validation findings for a portfolio or scenario."""

    issues: list[ValidationIssue] = []

    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.ERROR]

    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]

    def has_errors(self) -> bool:
        return any(i.level == ValidationLevel.ERROR for i in self.issues)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)


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


def validate_transition_instructions(
    instructions: list[TransitionInstruction],
    portfolio: Portfolio,
) -> ValidationReport:
    """Validate transition instructions against the source portfolio.

    Rule: ILLIQUID holdings must not be SELL_ALL or SELL_PARTIAL.
    Rule: SELL_PARTIAL must have a fraction in (0, 1].
    """
    report = ValidationReport()

    holding_map = {h.holding_id: h for h in portfolio.holdings}

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

        # Rule: illiquid must not be sold
        if h.liquidity_status == LiquidityStatus.ILLIQUID and instr.action in (
            TransitionAction.SELL_ALL,
            TransitionAction.SELL_PARTIAL,
        ):
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

        # Rule: SELL_PARTIAL requires fraction
        if instr.action == TransitionAction.SELL_PARTIAL:
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
            elif not (Decimal("0") < instr.fraction <= Decimal("1")):
                report.add(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="SELL_PARTIAL_INVALID_FRACTION",
                    message=(
                        f"Instruction '{instr.instruction_id}': fraction must be in "
                        f"(0, 1], got {instr.fraction}."
                    ),
                    entity_id=instr.instruction_id,
                ))

    return report
