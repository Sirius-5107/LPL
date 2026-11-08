"""Tests for data models."""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from lpl.models.account import Account, AccountType
from lpl.models.holding import (
    Holding,
    AssetClass,
    LiquidityStatus,
    CostBasisStatus,
    FractionalTransitionEligibility,
)
from lpl.models.product import AnnuityTerms, FeeStructure, Investment, RateInterpretation
from lpl.models.portfolio import Portfolio, PortfolioLabel, PortfolioSummary
from lpl.models.assumptions import Assumption, AssumptionStatus, AssumptionsRegister, UnresolvedStatus
from lpl.models.transition import TransitionInstruction, TransitionAction, TransitionEligibility
from lpl.models.scenario import Scenario, ScenarioType


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

def test_account_type_values():
    """AccountType enum must include all required account types."""
    types = {e.value for e in AccountType}
    assert "taxable_brokerage" in types
    assert "traditional_ira" in types
    assert "roth_ira" in types
    assert "annuity" in types
    assert "unknown" in types


def test_account_creation():
    acct = Account(account_id="A1", account_type=AccountType.TAXABLE_BROKERAGE, label="Brokerage")
    assert acct.account_type == AccountType.TAXABLE_BROKERAGE


# ---------------------------------------------------------------------------
# Holding
# ---------------------------------------------------------------------------

def test_holding_known_cost_basis():
    h = Holding(
        holding_id="H1",
        account_id="A1",
        label="S&P 500 fund",
        market_value=Decimal("50000"),
        cost_basis=Decimal("10000"),
        cost_basis_status=CostBasisStatus.KNOWN,
    )
    assert h.cost_basis == Decimal("10000")
    assert h.cost_basis_status == CostBasisStatus.KNOWN


def test_holding_unknown_cost_basis_is_none():
    """Unknown cost basis must be None — not zero."""
    h = Holding(
        holding_id="H2",
        account_id="A1",
        label="Annuity",
        market_value=Decimal("100000"),
        cost_basis=None,
        cost_basis_status=CostBasisStatus.UNKNOWN,
    )
    assert h.cost_basis is None


def test_holding_cost_basis_consistency_error():
    """cost_basis provided but status=UNKNOWN should raise ValidationError."""
    with pytest.raises(ValidationError):
        Holding(
            holding_id="H3",
            account_id="A1",
            label="Bad",
            market_value=Decimal("1000"),
            cost_basis=Decimal("500"),
            cost_basis_status=CostBasisStatus.UNKNOWN,  # inconsistent
        )


def test_holding_cost_basis_known_but_none_raises():
    """status=KNOWN but cost_basis=None should raise ValidationError."""
    with pytest.raises(ValidationError):
        Holding(
            holding_id="H4",
            account_id="A1",
            label="Bad2",
            market_value=Decimal("1000"),
            cost_basis=None,
            cost_basis_status=CostBasisStatus.KNOWN,  # inconsistent
        )


def test_illiquid_holding():
    h = Holding(
        holding_id="H-RE",
        account_id="A4",
        label="Real estate",
        market_value=Decimal("250000"),
        cost_basis_status=CostBasisStatus.UNKNOWN,
        liquidity_status=LiquidityStatus.ILLIQUID,
    )
    assert h.liquidity_status == LiquidityStatus.ILLIQUID


# ---------------------------------------------------------------------------
# AnnuityTerms — rate fields must not be conflated
# ---------------------------------------------------------------------------

def test_annuity_terms_unresolved():
    """An annuity with an unresolved rate must have UNRESOLVED interpretation."""
    terms = AnnuityTerms(
        rate_description="3% fixed lifetime income",
        rate_interpretation=RateInterpretation.UNRESOLVED,
    )
    assert terms.payout_rate is None
    assert terms.guaranteed_interest_rate is None
    assert terms.withdrawal_rate is None
    assert terms.rate_interpretation == RateInterpretation.UNRESOLVED


def test_annuity_terms_distinct_fields():
    """Payout rate, guaranteed interest rate, and withdrawal rate are separate fields."""
    terms = AnnuityTerms(
        payout_rate=Decimal("0.03"),
        guaranteed_interest_rate=Decimal("0.025"),
        withdrawal_rate=Decimal("0.10"),
        rate_description="illustrative with all fields",
        rate_interpretation=RateInterpretation.PAYOUT_RATE,
    )
    assert terms.payout_rate != terms.guaranteed_interest_rate
    assert terms.payout_rate != terms.withdrawal_rate


# ---------------------------------------------------------------------------
# FeeStructure — one-time vs recurring must be separate
# ---------------------------------------------------------------------------

def test_fee_structure_one_time_vs_recurring():
    fees = FeeStructure(
        expense_ratio=Decimal("0.0075"),
        exit_cost_pct=Decimal("0.01"),
    )
    assert fees.expense_ratio == Decimal("0.0075")   # recurring
    assert fees.exit_cost_pct == Decimal("0.01")     # one-time
    assert fees.advisory_fee_annual is None
    assert fees.entry_cost_pct is None


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

def _make_simple_portfolio(label=PortfolioLabel.CI) -> Portfolio:
    acct = Account(account_id="A1", account_type=AccountType.TAXABLE_BROKERAGE, label="Test")
    h = Holding(
        holding_id="H1",
        account_id="A1",
        label="Fund",
        market_value=Decimal("100000"),
        cost_basis=Decimal("80000"),
        cost_basis_status=CostBasisStatus.KNOWN,
    )
    return Portfolio(
        portfolio_id=f"P-{label.value}",
        label=label,
        accounts=[acct],
        holdings=[h],
        total_market_value=Decimal("100000"),
    )


def test_portfolio_computed_total():
    p = _make_simple_portfolio()
    assert p.computed_total() == Decimal("100000")


def test_portfolio_summary():
    p = _make_simple_portfolio()
    s = PortfolioSummary.from_portfolio(p)
    assert s.holding_count == 1
    assert s.unresolved_cost_basis_count == 0
    assert s.illiquid_holding_count == 0


# ---------------------------------------------------------------------------
# Assumptions
# ---------------------------------------------------------------------------

def test_assumption_unresolved():
    a = Assumption(
        id="annuity_rate",
        description="Vanguard annuity rate interpretation",
        value=None,
        status=AssumptionStatus.UNRESOLVED,
        source="Dossier",
    )
    assert a.status == AssumptionStatus.UNRESOLVED
    assert a.value is None


def test_assumptions_register():
    reg = AssumptionsRegister()
    reg.add(Assumption(id="a1", description="test", status=AssumptionStatus.UNRESOLVED))
    reg.add(Assumption(id="a2", description="confirmed", status=AssumptionStatus.CONFIRMED, value=42))
    assert len(reg.unresolved()) == 1
    assert reg.get("a2").status == AssumptionStatus.CONFIRMED


def test_assumptions_register_duplicate_raises():
    reg = AssumptionsRegister()
    reg.add(Assumption(id="a1", description="test", status=AssumptionStatus.ASSUMED))
    with pytest.raises(ValueError, match="already registered"):
        reg.add(Assumption(id="a1", description="duplicate", status=AssumptionStatus.ASSUMED))


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------

def test_transition_instruction():
    instr = TransitionInstruction(
        instruction_id="I1",
        holding_id="H1",
        action=TransitionAction.SELL_ALL,
    )
    assert instr.action == TransitionAction.SELL_ALL
    assert instr.fraction is None


def test_transition_sell_partial_with_fraction():
    instr = TransitionInstruction(
        instruction_id="I2",
        holding_id="H1",
        action=TransitionAction.SELL_PARTIAL,
        fraction=Decimal("0.5"),
    )
    assert instr.fraction == Decimal("0.5")
