"""Validation hardening round 2 tests.

Covers:
- Separated sale_eligible vs exchange_eligible for RESTRICTED holdings
- Annuity EXCHANGE as blocking ERROR
- FeeStructure numeric validation (product.py)
- AnnuityTerms numeric validation (product.py)
- check_calculation_readiness() — typed, calculation-specific gating
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from lpl.models.account import Account, AccountType
from lpl.models.holding import (
    Holding,
    AssetClass,
    CostBasisStatus,
    FractionalTransitionEligibility,
    LiquidityStatus,
)
from lpl.models.portfolio import Portfolio, PortfolioLabel
from lpl.models.product import AnnuityTerms, FeeStructure, Investment, RateInterpretation
from lpl.models.transition import TransitionInstruction, TransitionAction
from lpl.validation.validators import (
    CalculationType,
    CalculationReadinessResult,
    ValidationLevel,
    check_calculation_readiness,
    validate_transition_instructions,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _account(account_id: str, account_type: AccountType = AccountType.TAXABLE_BROKERAGE) -> Account:
    return Account(account_id=account_id, account_type=account_type, label=account_id)


def _holding(
    holding_id: str,
    account_id: str = "A1",
    market_value: str = "100000",
    liquidity: LiquidityStatus = LiquidityStatus.LIQUID,
    asset_class: AssetClass = AssetClass.EQUITY,
    cost_basis_status: CostBasisStatus = CostBasisStatus.KNOWN,
    exchange_eligible: bool | None = None,
    sale_eligible: bool | None = None,
    fractional: FractionalTransitionEligibility = FractionalTransitionEligibility.ELIGIBLE,
) -> Holding:
    cost_basis = Decimal("1") if cost_basis_status == CostBasisStatus.KNOWN else None
    return Holding(
        holding_id=holding_id,
        account_id=account_id,
        label=holding_id,
        market_value=Decimal(market_value),
        cost_basis=cost_basis,
        cost_basis_status=cost_basis_status,
        liquidity_status=liquidity,
        fractional_eligible=fractional,
        asset_class=asset_class,
        exchange_eligible=exchange_eligible,
        sale_eligible=sale_eligible,
    )


def _portfolio(holdings: list[Holding], accounts: list[Account] | None = None) -> Portfolio:
    if accounts is None:
        accounts = [_account("A1")]
    total = sum(h.market_value for h in holdings)
    return Portfolio(
        portfolio_id="P1",
        label=PortfolioLabel.CI,
        accounts=accounts,
        holdings=holdings,
        total_market_value=total,
    )


def _instr(
    action: TransitionAction,
    holding_id: str = "H1",
    fraction: Decimal | None = None,
) -> TransitionInstruction:
    return TransitionInstruction(
        instruction_id="I1",
        holding_id=holding_id,
        action=action,
        fraction=fraction,
    )


def _annuity_product(holding_id: str, rate_interpretation: RateInterpretation) -> Investment:
    return Investment(
        product_id=f"PROD-{holding_id}",
        label=f"Annuity for {holding_id}",
        annuity_terms=AnnuityTerms(
            rate_description="3% fixed lifetime income",
            rate_interpretation=rate_interpretation,
            payout_rate=Decimal("0.03") if rate_interpretation != RateInterpretation.UNRESOLVED else None,
        ),
    )


# ===========================================================================
# A. Separated sale/exchange eligibility for RESTRICTED holdings
# ===========================================================================

class TestRestrictedSaleVsExchangeEligibility:

    def test_restricted_sell_all_blocked_no_sale_eligible(self):
        """RESTRICTED + sale_eligible=None + SELL_ALL → blocking ERROR."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     sale_eligible=None, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "RESTRICTED_SALE_ELIGIBILITY_UNKNOWN"]
        assert len(errors) == 1
        assert report.has_errors()

    def test_restricted_sell_all_blocked_sale_eligible_false(self):
        """RESTRICTED + sale_eligible=False + SELL_ALL → blocking ERROR."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     sale_eligible=False, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "RESTRICTED_SALE_NOT_ELIGIBLE"]
        assert len(errors) == 1

    def test_restricted_sell_all_approved(self):
        """RESTRICTED + sale_eligible=True + SELL_ALL → no RESTRICTED_SALE error."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     sale_eligible=True, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        sale_errors = [i for i in report.errors() if "RESTRICTED_SALE" in i.code]
        assert len(sale_errors) == 0

    def test_restricted_sell_partial_blocked(self):
        """RESTRICTED + sale_eligible=None + SELL_PARTIAL → blocking ERROR."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     sale_eligible=None, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("0.5"))
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "RESTRICTED_SALE_ELIGIBILITY_UNKNOWN"]
        assert len(errors) == 1

    def test_restricted_exchange_blocked_no_exchange_eligible(self):
        """RESTRICTED + exchange_eligible=None + EXCHANGE → blocking ERROR."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     exchange_eligible=None, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "RESTRICTED_EXCHANGE_ELIGIBILITY_UNKNOWN"]
        assert len(errors) == 1

    def test_restricted_exchange_approved(self):
        """RESTRICTED + exchange_eligible=True + EXCHANGE → no RESTRICTED_EXCHANGE error."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     exchange_eligible=True, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        restricted_errors = [i for i in report.errors() if "RESTRICTED_EXCHANGE" in i.code]
        assert len(restricted_errors) == 0

    def test_exchange_eligible_does_not_authorize_sell(self):
        """exchange_eligible=True must NOT authorize SELL_ALL on a RESTRICTED holding."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     exchange_eligible=True, sale_eligible=None,
                     cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        # Must still produce a RESTRICTED_SALE error — exchange_eligible is irrelevant to sales
        sale_errors = [i for i in report.errors() if "RESTRICTED_SALE" in i.code]
        assert len(sale_errors) >= 1, (
            "exchange_eligible=True must not authorize a SELL on a RESTRICTED holding. "
            f"Issues found: {[(i.code, i.level) for i in report.issues]}"
        )

    def test_sale_eligible_does_not_authorize_exchange(self):
        """sale_eligible=True must NOT authorize EXCHANGE on a RESTRICTED holding."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     sale_eligible=True, exchange_eligible=None,
                     cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        # Must still produce a RESTRICTED_EXCHANGE error — sale_eligible is irrelevant to exchanges
        exchange_errors = [i for i in report.errors() if "RESTRICTED_EXCHANGE" in i.code]
        assert len(exchange_errors) >= 1, (
            "sale_eligible=True must not authorize an EXCHANGE on a RESTRICTED holding. "
            f"Issues found: {[(i.code, i.level) for i in report.issues]}"
        )


# ===========================================================================
# B. Annuity EXCHANGE is a blocking ERROR without explicit approval
# ===========================================================================

class TestAnnuityExchangeBlocking:

    def test_annuity_exchange_blocked_without_approval(self):
        """ANNUITY + exchange_eligible=None + EXCHANGE → blocking ERROR."""
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     liquidity=LiquidityStatus.LIQUID,
                     exchange_eligible=None, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "ANNUITY_EXCHANGE_NOT_APPROVED"]
        assert len(errors) == 1
        assert report.has_errors()

    def test_annuity_exchange_approved(self):
        """ANNUITY + exchange_eligible=True → no ANNUITY_EXCHANGE_NOT_APPROVED error."""
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     liquidity=LiquidityStatus.LIQUID,
                     exchange_eligible=True, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "ANNUITY_EXCHANGE_NOT_APPROVED"]
        assert len(errors) == 0


# ===========================================================================
# C. FeeStructure numeric validation
# ===========================================================================

class TestFeeStructureValidation:

    def test_fee_structure_negative_expense_ratio(self):
        with pytest.raises(ValidationError):
            FeeStructure(expense_ratio=Decimal("-0.001"))

    def test_fee_structure_zero_valid(self):
        fs = FeeStructure(expense_ratio=Decimal("0"))
        assert fs.expense_ratio == Decimal("0")

    def test_fee_structure_negative_advisory_fee(self):
        with pytest.raises(ValidationError):
            FeeStructure(advisory_fee_annual=Decimal("-0.005"))

    def test_fee_structure_negative_exit_cost_pct(self):
        with pytest.raises(ValidationError):
            FeeStructure(exit_cost_pct=Decimal("-0.01"))

    def test_fee_structure_negative_entry_cost_pct(self):
        with pytest.raises(ValidationError):
            FeeStructure(entry_cost_pct=Decimal("-0.005"))

    def test_fee_structure_negative_other_one_time(self):
        with pytest.raises(ValidationError):
            FeeStructure(other_one_time=Decimal("-100"))

    def test_fee_structure_negative_other_recurring(self):
        with pytest.raises(ValidationError):
            FeeStructure(other_recurring=Decimal("-50"))

    def test_fee_structure_valid_reference_values(self):
        """Reference client values: expense_ratio=0.0075, exit_cost_pct=0.01."""
        fs = FeeStructure(expense_ratio=Decimal("0.0075"), exit_cost_pct=Decimal("0.01"))
        assert fs.expense_ratio == Decimal("0.0075")
        assert fs.exit_cost_pct == Decimal("0.01")


# ===========================================================================
# D. AnnuityTerms numeric validation
# ===========================================================================

class TestAnnuityTermsValidation:

    def test_annuity_terms_negative_payout_rate(self):
        with pytest.raises(ValidationError):
            AnnuityTerms(
                rate_description="3% fixed lifetime income",
                payout_rate=Decimal("-0.03"),
            )

    def test_annuity_terms_negative_guaranteed_interest_rate(self):
        with pytest.raises(ValidationError):
            AnnuityTerms(
                rate_description="test",
                guaranteed_interest_rate=Decimal("-0.01"),
            )

    def test_annuity_terms_negative_withdrawal_rate(self):
        with pytest.raises(ValidationError):
            AnnuityTerms(
                rate_description="test",
                withdrawal_rate=Decimal("-0.05"),
            )

    def test_annuity_terms_negative_surrender_period(self):
        with pytest.raises(ValidationError):
            AnnuityTerms(
                rate_description="test",
                surrender_period_years=-1,
            )

    def test_annuity_terms_zero_valid(self):
        """Zero values must be accepted."""
        at = AnnuityTerms(
            rate_description="test",
            payout_rate=Decimal("0"),
            guaranteed_interest_rate=Decimal("0"),
            withdrawal_rate=Decimal("0"),
            surrender_period_years=0,
        )
        assert at.payout_rate == Decimal("0")
        assert at.surrender_period_years == 0

    def test_annuity_terms_valid_reference_values(self):
        """3% = 0.03 decimal fraction — reference dossier value."""
        at = AnnuityTerms(
            rate_description="3% fixed lifetime income",
            rate_interpretation=RateInterpretation.UNRESOLVED,
        )
        assert at.rate_interpretation == RateInterpretation.UNRESOLVED
        assert at.payout_rate is None  # Still unresolved


# ===========================================================================
# E. check_calculation_readiness — typed, calculation-specific gating
# ===========================================================================

class TestCheckCalculationReadiness:

    def test_readiness_tax_basis_blocked_by_unknown_cost_basis(self):
        """TAX_BASIS blocked when cost_basis_status=UNKNOWN."""
        h = _holding("H1", cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        results = check_calculation_readiness(p, CalculationType.TAX_BASIS)
        assert len(results) == 1
        assert results[0].holding_id == "H1"
        assert results[0].is_ready is False
        assert results[0].blocking_reason is not None

    def test_readiness_historical_return_not_blocked_by_unknown_cost_basis(self):
        """HISTORICAL_RETURN is NOT blocked by missing cost basis."""
        h = _holding("H1", cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        results = check_calculation_readiness(p, CalculationType.HISTORICAL_RETURN)
        assert len(results) == 1
        assert results[0].is_ready is True
        assert results[0].blocking_reason is None

    def test_readiness_annuity_income_blocked_by_unresolved_terms(self):
        """ANNUITY_INCOME blocked when rate_interpretation=UNRESOLVED."""
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        product = _annuity_product("H1", RateInterpretation.UNRESOLVED)
        results = check_calculation_readiness(
            p, CalculationType.ANNUITY_INCOME, product_map={"H1": product}
        )
        assert len(results) == 1
        assert results[0].is_ready is False
        assert "UNRESOLVED" in (results[0].blocking_reason or "")

    def test_readiness_annuity_income_ready_with_resolved_terms(self):
        """ANNUITY_INCOME ready when rate_interpretation is resolved."""
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        product = _annuity_product("H1", RateInterpretation.PAYOUT_RATE)
        results = check_calculation_readiness(
            p, CalculationType.ANNUITY_INCOME, product_map={"H1": product}
        )
        assert len(results) == 1
        assert results[0].is_ready is True

    def test_readiness_annuity_income_blocked_no_product_map(self):
        """ANNUITY_INCOME blocked when no product_map provided for annuity holding."""
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        results = check_calculation_readiness(
            p, CalculationType.ANNUITY_INCOME, product_map=None
        )
        assert len(results) == 1
        assert results[0].is_ready is False
        assert "product_map" in (results[0].blocking_reason or "").lower()

    def test_readiness_non_annuity_holding_annuity_income_check_ready(self):
        """Non-annuity holdings are ready for ANNUITY_INCOME check (not applicable)."""
        h = _holding("H1", asset_class=AssetClass.EQUITY,
                     cost_basis_status=CostBasisStatus.KNOWN)
        p = _portfolio([h])
        results = check_calculation_readiness(p, CalculationType.ANNUITY_INCOME)
        assert results[0].is_ready is True

    def test_readiness_cost_analysis_blocked_no_product_map(self):
        """COST_ANALYSIS blocked when product_map is None."""
        h = _holding("H1", cost_basis_status=CostBasisStatus.KNOWN)
        p = _portfolio([h])
        results = check_calculation_readiness(p, CalculationType.COST_ANALYSIS, product_map=None)
        assert results[0].is_ready is False

    def test_readiness_cost_analysis_ready_with_product(self):
        """COST_ANALYSIS ready when product is in product_map."""
        h = _holding("H1", cost_basis_status=CostBasisStatus.KNOWN)
        p = _portfolio([h])
        product = Investment(product_id="PROD-H1", label="Test Fund")
        results = check_calculation_readiness(
            p, CalculationType.COST_ANALYSIS, product_map={"H1": product}
        )
        assert results[0].is_ready is True

    def test_readiness_result_is_typed(self):
        """check_calculation_readiness returns CalculationReadinessResult instances."""
        h = _holding("H1", cost_basis_status=CostBasisStatus.KNOWN)
        p = _portfolio([h])
        results = check_calculation_readiness(p, CalculationType.TAX_BASIS)
        assert all(isinstance(r, CalculationReadinessResult) for r in results)

    def test_readiness_one_result_per_holding(self):
        """Returns exactly one result per holding in the portfolio."""
        holdings = [
            _holding("H1", cost_basis_status=CostBasisStatus.KNOWN),
            _holding("H2", cost_basis_status=CostBasisStatus.UNKNOWN),
        ]
        # Both use A1 account; total = 200000
        p = Portfolio(
            portfolio_id="P1",
            label=PortfolioLabel.CI,
            accounts=[_account("A1")],
            holdings=holdings,
            total_market_value=Decimal("200000"),
        )
        results = check_calculation_readiness(p, CalculationType.TAX_BASIS)
        assert len(results) == 2
        assert {r.holding_id for r in results} == {"H1", "H2"}
