"""Hardened validation tests — Day 2 validation layer.

Covers:
A. Fractional transition eligibility
B. Restricted and illiquid holding rules
C. IRA-to-Roth conversion constraints
D. Negative monetary and percentage field validation (model-level)
E. ValidationReport mutable default isolation
F. validate_calculation_readiness() — unknown data signals
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
from lpl.models.transition import TransitionInstruction, TransitionAction
from lpl.validation.validators import (
    ValidationLevel,
    ValidationReport,
    ValidationIssue,
    validate_transition_instructions,
    validate_calculation_readiness,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _account(account_id: str, account_type: AccountType = AccountType.TAXABLE_BROKERAGE) -> Account:
    return Account(account_id=account_id, account_type=account_type, label=account_id)


def _holding(
    holding_id: str,
    account_id: str = "A1",
    market_value: str = "100000",
    liquidity: LiquidityStatus = LiquidityStatus.LIQUID,
    fractional: FractionalTransitionEligibility = FractionalTransitionEligibility.ELIGIBLE,
    asset_class: AssetClass = AssetClass.EQUITY,
    cost_basis_status: CostBasisStatus = CostBasisStatus.KNOWN,
    exchange_eligible: bool | None = None,
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
    destination_account_id: str | None = None,
) -> TransitionInstruction:
    return TransitionInstruction(
        instruction_id="I1",
        holding_id=holding_id,
        action=action,
        fraction=fraction,
        destination_account_id=destination_account_id,
    )


# ===========================================================================
# A. Fractional transition eligibility
# ===========================================================================

class TestFractionalEligibility:

    def test_sell_partial_eligible_holding_valid_fraction(self):
        h = _holding("H1", fractional=FractionalTransitionEligibility.ELIGIBLE)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("0.5"))
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if "FRACTIONAL" in i.code or "SELL_PARTIAL" in i.code]
        assert len(errors) == 0

    def test_sell_partial_ineligible_holding_blocked(self):
        h = _holding("H1", fractional=FractionalTransitionEligibility.INELIGIBLE)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("0.5"))
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "SELL_PARTIAL_FRACTIONAL_INELIGIBLE"]
        assert len(errors) == 1

    def test_sell_partial_unknown_fractional_eligibility_is_warning(self):
        h = _holding("H1", fractional=FractionalTransitionEligibility.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("0.5"))
        report = validate_transition_instructions([instr], p)
        warnings = [i for i in report.warnings() if i.code == "SELL_PARTIAL_FRACTIONAL_ELIGIBILITY_UNKNOWN"]
        assert len(warnings) == 1

    def test_sell_partial_fraction_zero_invalid(self):
        h = _holding("H1", fractional=FractionalTransitionEligibility.ELIGIBLE)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("0"))
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "SELL_PARTIAL_INVALID_FRACTION"]
        assert len(errors) == 1

    def test_sell_partial_fraction_one_invalid(self):
        """fraction=1 is invalid for SELL_PARTIAL — use SELL_ALL instead."""
        h = _holding("H1", fractional=FractionalTransitionEligibility.ELIGIBLE)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("1"))
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "SELL_PARTIAL_INVALID_FRACTION"]
        assert len(errors) == 1

    def test_sell_partial_fraction_gt_one_invalid(self):
        h = _holding("H1", fractional=FractionalTransitionEligibility.ELIGIBLE)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("1.5"))
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "SELL_PARTIAL_INVALID_FRACTION"]
        assert len(errors) == 1

    def test_sell_partial_missing_fraction_error(self):
        h = _holding("H1", fractional=FractionalTransitionEligibility.ELIGIBLE)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=None)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "SELL_PARTIAL_MISSING_FRACTION"]
        assert len(errors) == 1

    def test_sell_all_with_fraction_produces_warning(self):
        h = _holding("H1")
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL, fraction=Decimal("0.5"))
        report = validate_transition_instructions([instr], p)
        warnings = [i for i in report.warnings() if i.code == "SELL_ALL_FRACTION_IGNORED"]
        assert len(warnings) == 1

    def test_sell_all_no_fraction_no_warning(self):
        h = _holding("H1")
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        warnings = [i for i in report.warnings() if i.code == "SELL_ALL_FRACTION_IGNORED"]
        assert len(warnings) == 0


# ===========================================================================
# B. Restricted and illiquid holdings
# ===========================================================================

class TestRestrictedAndIlliquid:

    def test_illiquid_sell_all_blocked(self):
        h = _holding("H1", liquidity=LiquidityStatus.ILLIQUID, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "ILLIQUID_TRANSITION_ATTEMPT"]
        assert len(errors) == 1

    def test_illiquid_sell_partial_blocked(self):
        h = _holding("H1", liquidity=LiquidityStatus.ILLIQUID, cost_basis_status=CostBasisStatus.UNKNOWN,
                     fractional=FractionalTransitionEligibility.INELIGIBLE)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_PARTIAL, fraction=Decimal("0.5"))
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "ILLIQUID_TRANSITION_ATTEMPT"]
        assert len(errors) == 1

    def test_illiquid_exchange_blocked(self):
        h = _holding("H1", liquidity=LiquidityStatus.ILLIQUID, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "ILLIQUID_TRANSITION_ATTEMPT"]
        assert len(errors) == 1

    def test_illiquid_retain_allowed(self):
        h = _holding("H1", liquidity=LiquidityStatus.ILLIQUID, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.RETAIN)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "ILLIQUID_TRANSITION_ATTEMPT"]
        assert len(errors) == 0

    def test_restricted_sell_unknown_eligibility_requires_manual_review(self):
        """Restricted holding with no exchange_eligible flag → WARNING for manual review."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     exchange_eligible=None, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        warnings = [i for i in report.warnings() if i.code == "RESTRICTED_TRANSITION_REQUIRES_MANUAL_REVIEW"]
        assert len(warnings) == 1
        # Must not be a silent pass
        assert not any(i.level == ValidationLevel.INFO and "RESTRICTED" in i.code for i in report.issues)

    def test_restricted_sell_explicitly_ineligible_blocked(self):
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     exchange_eligible=False, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "RESTRICTED_TRANSITION_NOT_ELIGIBLE"]
        assert len(errors) == 1

    def test_restricted_sell_explicitly_eligible_no_restriction_error(self):
        """If exchange_eligible=True, no RESTRICTED_TRANSITION error (annuity rule may still warn)."""
        h = _holding("H1", liquidity=LiquidityStatus.RESTRICTED,
                     exchange_eligible=True, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.SELL_ALL)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if "RESTRICTED_TRANSITION" in i.code]
        assert len(errors) == 0

    def test_annuity_exchange_without_explicit_eligibility_flagged(self):
        """ANNUITY EXCHANGE without exchange_eligible=True must require manual review."""
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     liquidity=LiquidityStatus.RESTRICTED,
                     exchange_eligible=None, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        warnings = [i for i in report.warnings() if i.code == "ANNUITY_EXCHANGE_NOT_CONFIRMED"]
        assert len(warnings) >= 1

    def test_annuity_exchange_with_explicit_eligibility_no_annuity_warning(self):
        """ANNUITY with exchange_eligible=True: ANNUITY_EXCHANGE_NOT_CONFIRMED not raised."""
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     liquidity=LiquidityStatus.LIQUID,
                     exchange_eligible=True, cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        instr = _instr(TransitionAction.EXCHANGE)
        report = validate_transition_instructions([instr], p)
        warnings = [i for i in report.warnings() if i.code == "ANNUITY_EXCHANGE_NOT_CONFIRMED"]
        assert len(warnings) == 0


# ===========================================================================
# C. IRA-to-Roth conversion constraints
# ===========================================================================

class TestConvertConstraints:

    def _make_convert_portfolio(
        self,
        source_type: AccountType = AccountType.TRADITIONAL_IRA,
        dest_type: AccountType = AccountType.ROTH_IRA,
    ) -> tuple[Portfolio, str, str]:
        """Returns (portfolio, source_holding_id, dest_account_id)."""
        src_acct = _account("SRC", source_type)
        dst_acct = _account("DST", dest_type)
        src_holding = _holding("H_SRC", account_id="SRC",
                               cost_basis_status=CostBasisStatus.INAPPLICABLE)
        # destination is an empty account (no holdings needed for validation)
        total = src_holding.market_value
        p = Portfolio(
            portfolio_id="P1",
            label=PortfolioLabel.CI,
            accounts=[src_acct, dst_acct],
            holdings=[src_holding],
            total_market_value=total,
        )
        return p, "H_SRC", "DST"

    def test_valid_convert_traditional_ira_to_roth(self):
        p, h_id, dst_id = self._make_convert_portfolio(
            AccountType.TRADITIONAL_IRA, AccountType.ROTH_IRA
        )
        instr = _instr(TransitionAction.CONVERT, holding_id=h_id, destination_account_id=dst_id)
        report = validate_transition_instructions([instr], p)
        convert_errors = [
            i for i in report.errors()
            if "CONVERT" in i.code
        ]
        assert len(convert_errors) == 0, convert_errors

    def test_convert_invalid_source_type(self):
        """Taxable brokerage as source of CONVERT must fail."""
        p, h_id, dst_id = self._make_convert_portfolio(
            AccountType.TAXABLE_BROKERAGE, AccountType.ROTH_IRA
        )
        instr = _instr(TransitionAction.CONVERT, holding_id=h_id, destination_account_id=dst_id)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "CONVERT_INVALID_SOURCE_ACCOUNT_TYPE"]
        assert len(errors) == 1

    def test_convert_missing_destination_account_id(self):
        p, h_id, _ = self._make_convert_portfolio(
            AccountType.TRADITIONAL_IRA, AccountType.ROTH_IRA
        )
        instr = _instr(TransitionAction.CONVERT, holding_id=h_id, destination_account_id=None)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "CONVERT_MISSING_DESTINATION"]
        assert len(errors) == 1

    def test_convert_wrong_destination_type(self):
        """TRAD IRA → TRAD IRA must fail (not a Roth conversion)."""
        p, h_id, dst_id = self._make_convert_portfolio(
            AccountType.TRADITIONAL_IRA, AccountType.TRADITIONAL_IRA
        )
        instr = _instr(TransitionAction.CONVERT, holding_id=h_id, destination_account_id=dst_id)
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "CONVERT_INVALID_DESTINATION_ACCOUNT_TYPE"]
        assert len(errors) == 1

    def test_convert_destination_account_not_in_portfolio(self):
        p, h_id, _ = self._make_convert_portfolio(
            AccountType.TRADITIONAL_IRA, AccountType.ROTH_IRA
        )
        instr = _instr(TransitionAction.CONVERT, holding_id=h_id, destination_account_id="NONEXISTENT")
        report = validate_transition_instructions([instr], p)
        errors = [i for i in report.errors() if i.code == "CONVERT_DESTINATION_ACCOUNT_MISSING"]
        assert len(errors) == 1


# ===========================================================================
# D. Negative monetary and percentage field validation
# ===========================================================================

class TestNegativeFieldValidation:

    def _base_holding_kwargs(self) -> dict:
        return dict(
            holding_id="H1",
            account_id="A1",
            label="Test",
            cost_basis=Decimal("1000"),
            cost_basis_status=CostBasisStatus.KNOWN,
        )

    def test_negative_market_value_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            Holding(
                market_value=Decimal("-1"),
                **self._base_holding_kwargs(),
            )
        assert "market_value" in str(exc_info.value).lower() or "0" in str(exc_info.value)

    def test_zero_market_value_allowed(self):
        h = Holding(market_value=Decimal("0"), **self._base_holding_kwargs())
        assert h.market_value == Decimal("0")

    def test_negative_cost_basis_rejected(self):
        with pytest.raises(ValidationError):
            Holding(
                holding_id="H1",
                account_id="A1",
                label="Test",
                market_value=Decimal("1000"),
                cost_basis=Decimal("-1"),
                cost_basis_status=CostBasisStatus.KNOWN,
            )

    def test_negative_expense_ratio_rejected(self):
        with pytest.raises(ValidationError):
            Holding(
                holding_id="H1",
                account_id="A1",
                label="Test",
                market_value=Decimal("1000"),
                cost_basis_status=CostBasisStatus.INAPPLICABLE,
                expense_ratio=Decimal("-0.01"),
            )

    def test_negative_exit_cost_pct_rejected(self):
        with pytest.raises(ValidationError):
            Holding(
                holding_id="H1",
                account_id="A1",
                label="Test",
                market_value=Decimal("1000"),
                cost_basis_status=CostBasisStatus.INAPPLICABLE,
                exit_cost_pct=Decimal("-0.005"),
            )

    def test_zero_expense_ratio_allowed(self):
        h = Holding(
            holding_id="H1", account_id="A1", label="Test",
            market_value=Decimal("1000"),
            cost_basis_status=CostBasisStatus.INAPPLICABLE,
            expense_ratio=Decimal("0"),
        )
        assert h.expense_ratio == Decimal("0")

    def test_valid_expense_ratio_075pct(self):
        """0.0075 = 0.75% — existing reference data value must be accepted."""
        h = Holding(
            holding_id="H1", account_id="A1", label="Test",
            market_value=Decimal("50000"),
            cost_basis=Decimal("10000"),
            cost_basis_status=CostBasisStatus.KNOWN,
            expense_ratio=Decimal("0.0075"),
            exit_cost_pct=Decimal("0.01"),
        )
        assert h.expense_ratio == Decimal("0.0075")
        assert h.exit_cost_pct == Decimal("0.01")


# ===========================================================================
# E. ValidationReport mutable default isolation
# ===========================================================================

class TestValidationReportIsolation:

    def test_two_reports_do_not_share_issues(self):
        """Each ValidationReport instance must have its own issues list."""
        r1 = ValidationReport()
        r2 = ValidationReport()
        r1.add(ValidationIssue(
            level=ValidationLevel.ERROR,
            code="TEST_ERROR",
            message="Only in r1",
        ))
        assert len(r1.issues) == 1
        assert len(r2.issues) == 0, "r2 must not share r1's issues list"

    def test_default_issues_list_is_empty(self):
        r = ValidationReport()
        assert r.issues == []

    def test_add_then_check_has_errors(self):
        r = ValidationReport()
        assert not r.has_errors()
        r.add(ValidationIssue(level=ValidationLevel.ERROR, code="X", message="test"))
        assert r.has_errors()


# ===========================================================================
# F. validate_calculation_readiness — unknown data signals
# ===========================================================================

class TestCalculationReadiness:

    def test_unknown_cost_basis_produces_warning(self):
        h = _holding("H1", cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        report = validate_calculation_readiness(p)
        warnings = [i for i in report.warnings() if i.code == "CALC_MISSING_COST_BASIS"]
        assert len(warnings) >= 1

    def test_partial_cost_basis_produces_warning(self):
        h = _holding("H1", cost_basis_status=CostBasisStatus.PARTIAL)
        p = _portfolio([h])
        report = validate_calculation_readiness(p)
        warnings = [i for i in report.warnings() if i.code == "CALC_MISSING_COST_BASIS"]
        assert len(warnings) >= 1

    def test_known_cost_basis_no_missing_basis_warning(self):
        h = _holding("H1", cost_basis_status=CostBasisStatus.KNOWN)
        p = _portfolio([h])
        report = validate_calculation_readiness(p)
        warnings = [i for i in report.warnings() if i.code == "CALC_MISSING_COST_BASIS"]
        assert len(warnings) == 0

    def test_annuity_holding_produces_rate_check_warning(self):
        h = _holding("H1", asset_class=AssetClass.ANNUITY,
                     cost_basis_status=CostBasisStatus.UNKNOWN)
        p = _portfolio([h])
        report = validate_calculation_readiness(p)
        warnings = [i for i in report.warnings() if i.code == "CALC_ANNUITY_TERMS_CHECK_REQUIRED"]
        assert len(warnings) >= 1

    def test_non_annuity_no_annuity_warning(self):
        h = _holding("H1", asset_class=AssetClass.EQUITY, cost_basis_status=CostBasisStatus.KNOWN)
        p = _portfolio([h])
        report = validate_calculation_readiness(p)
        warnings = [i for i in report.warnings() if i.code == "CALC_ANNUITY_TERMS_CHECK_REQUIRED"]
        assert len(warnings) == 0

    def test_unknown_account_type_produces_warning(self):
        acct = _account("A_UNK", AccountType.UNKNOWN)
        h = Holding(
            holding_id="H1", account_id="A_UNK", label="H1",
            market_value=Decimal("100000"),
            cost_basis_status=CostBasisStatus.UNKNOWN,
        )
        p = Portfolio(
            portfolio_id="P1", label=PortfolioLabel.CI,
            accounts=[acct], holdings=[h],
            total_market_value=Decimal("100000"),
        )
        report = validate_calculation_readiness(p)
        warnings = [i for i in report.warnings() if i.code == "CALC_UNKNOWN_ACCOUNT_TYPE"]
        assert len(warnings) >= 1

    def test_clean_portfolio_no_calc_warnings(self):
        """A portfolio with all known data produces no calculation readiness warnings."""
        h = _holding("H1", asset_class=AssetClass.EQUITY, cost_basis_status=CostBasisStatus.KNOWN)
        p = _portfolio([h])
        report = validate_calculation_readiness(p)
        # No errors
        assert not report.has_errors()
        # No CALC_ warnings
        calc_warnings = [i for i in report.warnings() if i.code.startswith("CALC_")]
        assert len(calc_warnings) == 0


# ===========================================================================
# G. Reference client loads and existing validation still passes
# ===========================================================================

class TestReferenceClientBackcompat:

    def test_reference_client_still_loads(self, reference_client):
        assert reference_client.client_id == "REF-001"

    def test_reference_client_ci_has_five_holdings(self, reference_client):
        assert len(reference_client.ci_portfolio.holdings) == 5

    def test_reference_client_ci_total_reconciles(self, reference_client):
        ci = reference_client.ci_portfolio
        assert ci.computed_total() == ci.total_market_value

    def test_reference_client_pi_total_reconciles(self, reference_client):
        pi = reference_client.pi_portfolio
        assert pi.computed_total() == pi.total_market_value

    def test_reference_client_annuity_holding_cost_basis_none(self, reference_client):
        h = next(h for h in reference_client.ci_portfolio.holdings if h.holding_id == "H-CI-02")
        assert h.cost_basis is None
        assert h.cost_basis_status == CostBasisStatus.UNKNOWN

    def test_reference_client_real_estate_illiquid(self, reference_client):
        h = next(h for h in reference_client.ci_portfolio.holdings if h.holding_id == "H-CI-04")
        assert h.liquidity_status == LiquidityStatus.ILLIQUID
