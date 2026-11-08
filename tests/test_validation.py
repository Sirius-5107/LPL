"""Tests for validation rules."""

from decimal import Decimal
import pytest

from lpl.models.account import Account, AccountType
from lpl.models.holding import Holding, LiquidityStatus, CostBasisStatus
from lpl.models.portfolio import Portfolio, PortfolioLabel
from lpl.models.transition import TransitionInstruction, TransitionAction
from lpl.validation.validators import (
    ValidationLevel,
    validate_portfolio,
    validate_ci_pi_separation,
    validate_transition_instructions,
)


def _make_portfolio(
    portfolio_id: str,
    label: PortfolioLabel,
    total: str,
    holding_values: list[str],
    liquid_statuses: list[LiquidityStatus] = None,
    cost_basis_statuses: list[CostBasisStatus] = None,
) -> Portfolio:
    acct = Account(account_id="A1", account_type=AccountType.TAXABLE_BROKERAGE, label="Test")
    if liquid_statuses is None:
        liquid_statuses = [LiquidityStatus.LIQUID] * len(holding_values)
    if cost_basis_statuses is None:
        cost_basis_statuses = [CostBasisStatus.KNOWN] * len(holding_values)
    holdings = []
    for i, (v, liq, cb) in enumerate(zip(holding_values, liquid_statuses, cost_basis_statuses)):
        cost_basis = Decimal("1") if cb == CostBasisStatus.KNOWN else None
        holdings.append(Holding(
            holding_id=f"H{i}",
            account_id="A1",
            label=f"Holding {i}",
            market_value=Decimal(v),
            cost_basis=cost_basis,
            cost_basis_status=cb,
            liquidity_status=liq,
        ))
    return Portfolio(
        portfolio_id=portfolio_id,
        label=label,
        accounts=[acct],
        holdings=holdings,
        total_market_value=Decimal(total),
    )


# ---------------------------------------------------------------------------
# Portfolio reconciliation
# ---------------------------------------------------------------------------

def test_portfolio_reconciles_ok():
    p = _make_portfolio("P1", PortfolioLabel.CI, "100000", ["60000", "40000"])
    report = validate_portfolio(p)
    errors = [i for i in report.errors() if i.code == "PORTFOLIO_TOTAL_MISMATCH"]
    assert len(errors) == 0


def test_portfolio_reconciliation_fails():
    p = _make_portfolio("P1", PortfolioLabel.CI, "100001", ["60000", "40000"])
    report = validate_portfolio(p)
    errors = [i for i in report.errors() if i.code == "PORTFOLIO_TOTAL_MISMATCH"]
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# Unknown cost basis flagged as warning
# ---------------------------------------------------------------------------

def test_unknown_cost_basis_flagged():
    p = _make_portfolio(
        "P1", PortfolioLabel.CI, "100000", ["100000"],
        cost_basis_statuses=[CostBasisStatus.UNKNOWN],
    )
    report = validate_portfolio(p)
    warnings = [i for i in report.warnings() if i.code == "MISSING_COST_BASIS"]
    assert len(warnings) == 1


def test_known_cost_basis_no_warning():
    p = _make_portfolio(
        "P1", PortfolioLabel.CI, "100000", ["100000"],
        cost_basis_statuses=[CostBasisStatus.KNOWN],
    )
    report = validate_portfolio(p)
    warnings = [i for i in report.warnings() if i.code == "MISSING_COST_BASIS"]
    assert len(warnings) == 0


# ---------------------------------------------------------------------------
# CI/PI separation
# ---------------------------------------------------------------------------

def test_ci_pi_different_ids():
    ci = _make_portfolio("P-CI", PortfolioLabel.CI, "100000", ["100000"])
    pi = _make_portfolio("P-PI", PortfolioLabel.PI, "100000", ["100000"])
    report = validate_ci_pi_separation(ci, pi)
    errors = [i for i in report.errors() if i.code == "CI_PI_SAME_ID"]
    assert len(errors) == 0


def test_ci_pi_same_id_raises():
    ci = _make_portfolio("SAME-ID", PortfolioLabel.CI, "100000", ["100000"])
    pi = _make_portfolio("SAME-ID", PortfolioLabel.PI, "100000", ["100000"])
    report = validate_ci_pi_separation(ci, pi)
    errors = [i for i in report.errors() if i.code == "CI_PI_SAME_ID"]
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# Illiquid transition guard
# ---------------------------------------------------------------------------

def test_illiquid_transition_blocked():
    p = _make_portfolio(
        "P1", PortfolioLabel.CI, "250000", ["250000"],
        liquid_statuses=[LiquidityStatus.ILLIQUID],
        cost_basis_statuses=[CostBasisStatus.UNKNOWN],
    )
    instr = TransitionInstruction(
        instruction_id="I1",
        holding_id="H0",
        action=TransitionAction.SELL_ALL,
    )
    report = validate_transition_instructions([instr], p)
    errors = [i for i in report.errors() if i.code == "ILLIQUID_TRANSITION_ATTEMPT"]
    assert len(errors) == 1


def test_illiquid_retain_is_ok():
    p = _make_portfolio(
        "P1", PortfolioLabel.CI, "250000", ["250000"],
        liquid_statuses=[LiquidityStatus.ILLIQUID],
        cost_basis_statuses=[CostBasisStatus.UNKNOWN],
    )
    instr = TransitionInstruction(
        instruction_id="I1",
        holding_id="H0",
        action=TransitionAction.RETAIN,
    )
    report = validate_transition_instructions([instr], p)
    errors = [i for i in report.errors() if i.code == "ILLIQUID_TRANSITION_ATTEMPT"]
    assert len(errors) == 0


def test_sell_partial_missing_fraction():
    p = _make_portfolio("P1", PortfolioLabel.CI, "100000", ["100000"])
    instr = TransitionInstruction(
        instruction_id="I1",
        holding_id="H0",
        action=TransitionAction.SELL_PARTIAL,
        fraction=None,
    )
    report = validate_transition_instructions([instr], p)
    errors = [i for i in report.errors() if i.code == "SELL_PARTIAL_MISSING_FRACTION"]
    assert len(errors) == 1


def test_sell_partial_invalid_fraction():
    p = _make_portfolio("P1", PortfolioLabel.CI, "100000", ["100000"])
    instr = TransitionInstruction(
        instruction_id="I1",
        holding_id="H0",
        action=TransitionAction.SELL_PARTIAL,
        fraction=Decimal("1.5"),  # > 1
    )
    report = validate_transition_instructions([instr], p)
    errors = [i for i in report.errors() if i.code == "SELL_PARTIAL_INVALID_FRACTION"]
    assert len(errors) == 1
