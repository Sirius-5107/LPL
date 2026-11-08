"""Tests for client loader and reference client JSON."""

from decimal import Decimal
from pathlib import Path
import pytest

from lpl.loaders.client_loader import load_client_from_json
from lpl.models.portfolio import PortfolioLabel
from lpl.models.holding import LiquidityStatus, CostBasisStatus
from lpl.models.account import AccountType
from lpl.models.product import RateInterpretation

REFERENCE_CLIENT_PATH = Path(__file__).parent.parent / "data" / "clients" / "reference_client.json"


def test_reference_client_loads():
    client = load_client_from_json(REFERENCE_CLIENT_PATH)
    assert client.client_id == "REF-001"


def test_reference_client_has_ci_and_pi(reference_client):
    assert reference_client.ci_portfolio is not None
    assert reference_client.pi_portfolio is not None


def test_ci_label(reference_client):
    assert reference_client.ci_portfolio.label == PortfolioLabel.CI


def test_pi_label(reference_client):
    assert reference_client.pi_portfolio.label == PortfolioLabel.PI


def test_ci_pi_different_ids(reference_client):
    assert reference_client.ci_portfolio.portfolio_id != reference_client.pi_portfolio.portfolio_id


def test_ci_total_market_value(reference_client):
    """CI total must be $700,000 per dossier."""
    assert reference_client.ci_portfolio.total_market_value == Decimal("700000")


def test_ci_has_five_holdings(reference_client):
    assert len(reference_client.ci_portfolio.holdings) == 5


def test_ci_sp500_sleeve(reference_client):
    """Sleeve 1: S&P 500 fund — $50k market value, $10k cost basis, 0.75% ER, 1% exit."""
    h = next(h for h in reference_client.ci_portfolio.holdings if h.holding_id == "H-CI-01")
    assert h.market_value == Decimal("50000")
    assert h.cost_basis == Decimal("10000")
    assert h.cost_basis_status == CostBasisStatus.KNOWN
    assert h.expense_ratio == Decimal("0.0075")
    assert h.exit_cost_pct == Decimal("0.01")


def test_ci_annuity_cost_basis_unknown(reference_client):
    """Sleeve 2: Vanguard annuity — cost basis must be None (unknown), not zero."""
    h = next(h for h in reference_client.ci_portfolio.holdings if h.holding_id == "H-CI-02")
    assert h.cost_basis is None
    assert h.cost_basis_status == CostBasisStatus.UNKNOWN


def test_ci_traditional_ira(reference_client):
    """Sleeve 3: Traditional IRA — $200k, cost basis inapplicable."""
    h = next(h for h in reference_client.ci_portfolio.holdings if h.holding_id == "H-CI-03")
    assert h.market_value == Decimal("200000")
    assert h.cost_basis_status == CostBasisStatus.INAPPLICABLE
    # Account type must be TRADITIONAL_IRA
    acct = next(a for a in reference_client.ci_portfolio.accounts if a.account_id == "ACCT-CI-03")
    assert acct.account_type == AccountType.TRADITIONAL_IRA


def test_ci_real_estate_illiquid(reference_client):
    """Sleeve 4: Real-estate fund — $250k, ILLIQUID."""
    h = next(h for h in reference_client.ci_portfolio.holdings if h.holding_id == "H-CI-04")
    assert h.market_value == Decimal("250000")
    assert h.liquidity_status == LiquidityStatus.ILLIQUID


def test_ci_alternatives_partially_liquid(reference_client):
    """Sleeve 5: Alternatives — $100k, PARTIALLY_LIQUID."""
    h = next(h for h in reference_client.ci_portfolio.holdings if h.holding_id == "H-CI-05")
    assert h.market_value == Decimal("100000")
    assert h.liquidity_status == LiquidityStatus.PARTIALLY_LIQUID


def test_ci_total_reconciles(reference_client):
    """CI holdings must sum to declared total."""
    ci = reference_client.ci_portfolio
    computed = ci.computed_total()
    assert computed == ci.total_market_value


def test_pi_has_roth_ira(reference_client):
    """PI must have a Roth IRA account (from conversion)."""
    pi = reference_client.pi_portfolio
    types = {a.account_type for a in pi.accounts}
    assert AccountType.ROTH_IRA in types


def test_no_tax_rates_fabricated(reference_client):
    """Client constraints must not contain invented tax rates."""
    assert reference_client.constraints.tax_filing_status is None


def test_missing_data_explicit_nulls(reference_client):
    """Client age, goals, and state of residence must be null — not invented."""
    assert reference_client.age is None
    assert reference_client.goals.target_retirement_age is None
    assert reference_client.constraints.state_of_residence is None


def test_load_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_client_from_json("/nonexistent/path/client.json")


def test_second_client_loadable(tmp_path):
    """A second client must be loadable without source code changes."""
    import json
    second = {
        "client_id": "CLIENT-002",
        "name": "Second Client",
        "age": 55,
        "goals": {},
        "constraints": {},
        "ci_portfolio": {
            "portfolio_id": "CLIENT-002-CI",
            "label": "CI",
            "total_market_value": "500000",
            "accounts": [
                {"account_id": "A1", "account_type": "taxable_brokerage", "label": "Main"}
            ],
            "holdings": [
                {
                    "holding_id": "H1",
                    "account_id": "A1",
                    "label": "Index fund",
                    "market_value": "500000",
                    "cost_basis": "300000",
                    "cost_basis_status": "known",
                }
            ],
        },
    }
    p = tmp_path / "client2.json"
    p.write_text(json.dumps(second))
    client2 = load_client_from_json(p)
    assert client2.client_id == "CLIENT-002"
    assert client2.ci_portfolio.total_market_value == Decimal("500000")
