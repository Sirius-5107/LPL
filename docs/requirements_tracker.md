# Requirements Tracker — Day 1

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| R-01 | Modular monolith in Python 3.11+ | DONE | Python 3.13 tested |
| R-02 | Pydantic data models (Client, Account, Holding, Portfolio, etc.) | DONE | All 8 model modules |
| R-03 | Reference client JSON (5 sleeves, CI and PI separate) | DONE | data/clients/reference_client.json |
| R-04 | A second client loadable without source code changes | DONE | test_second_client_loadable passes |
| R-05 | Missing cost basis must never silently become zero | DONE | CostBasisStatus + MissingCostBasisError |
| R-06 | Traditional IRA, Roth IRA, taxable brokerage, annuity are distinct account types | DONE | AccountType enum, separate tax treatment enforced |
| R-07 | Annuity payout rate / guaranteed rate / withdrawal rate are distinct fields | DONE | AnnuityTerms model; RateInterpretation.UNRESOLVED |
| R-08 | Illiquid assets must not be auto-transitioned | DONE | Validation rule + IlliquidAssetTransitionError |
| R-09 | One-time and recurring fees are separate | DONE | FeeStructure model |
| R-10 | Nominal and real values are distinguishable | DONE | Documented in contracts; real values always require explicit inflation input |
| R-11 | Gross and net performance are distinguishable | DONE | PerformanceEngineOutput has separate gross/net return fields |
| R-12 | Every assumption has source, status, version | DONE | Assumption model; AssumptionsRegister |
| R-13 | Unsupported calculations flagged, not approximated | DONE | UnsupportedCalculationError; is_supported fields in contracts |
| R-14 | No hardcoded reference client in business logic | DONE | load_client_from_json(path) only |
| R-15 | Module contracts for tax, costs, performance, retirement, decision | DONE | lpl/contracts/ |
| R-16 | Portfolio reconciliation validation | DONE | validate_portfolio() |
| R-17 | Allocation weight validation | DEFERRED | allocation_weight field does not exist on Holding or Portfolio models. The field is not in the current schema. Implementing sum-to-1 validation requires the field to be modelled first. No allocation schema has been invented to satisfy this requirement. |
| R-18 | Illiquid constraint in transition validation | DONE | validate_transition_instructions() — now also blocks EXCHANGE on ILLIQUID holdings |
| R-19 | CI/PI separation validation | DONE | validate_ci_pi_separation() |
| R-20 | Assumptions register | DONE | docs/assumptions_register.md |
| R-21 | Data dictionary | DONE | docs/data_dictionary.md |
| R-22 | Architecture document | DONE | docs/architecture.md |
| R-23 | Setup instructions | DONE | README.md |
| R-24 | Test report (actual run results) | DONE | tests/test_report.md — 45/45 passed |
| R-25 | Decimal used for monetary precision | DONE | All market_value, cost_basis, fee fields are Decimal |
| R-26 | No invented tax rules or default tax rates | DONE | No tax rate defaults anywhere; Optional fields only |
| R-27 | No empty placeholder modules | DONE | All modules have substantive content |
| R-28 | Type hints throughout | DONE | All models and functions are fully typed |
| R-29 | Explicit exceptions and validation errors | DONE | exceptions.py; pydantic ValidationError on model load |

| R-30 | Fractional transition eligibility enforced in validation | DONE | SELL_PARTIAL blocked for INELIGIBLE holdings; UNKNOWN triggers warning |
| R-31 | RESTRICTED holding sale requires explicit sale_eligible=True | DONE | Holding.sale_eligible field; SELL_ALL/SELL_PARTIAL blocked with ERROR if not True |
| R-31b | RESTRICTED holding exchange requires explicit exchange_eligible=True | DONE | Holding.exchange_eligible field; EXCHANGE blocked with ERROR if not True |
| R-31c | sale_eligible and exchange_eligible are entirely independent | DONE | Each field governs its own action type only; neither authorises the other |
| R-32 | Annuity EXCHANGE requires exchange_eligible=True — blocking ERROR | DONE | ANNUITY_EXCHANGE_NOT_APPROVED code; changed from WARNING to ERROR |
| R-33 | CONVERT enforces TRADITIONAL_IRA → ROTH_IRA only | DONE | validate_transition_instructions(); destination_account_id required |
| R-34 | Negative monetary/percentage fields rejected at model level | DONE | Pydantic field_validators on Holding and FeeStructure and AnnuityTerms |
| R-35 | ValidationReport instances do not share mutable state | DONE | Field(default_factory=list) |
| R-36 | validate_calculation_readiness() reports missing/unresolved data | DONE | Returns warnings for UNKNOWN cost basis, ANNUITY asset class, UNKNOWN account type |
| R-37 | Typed calculation-specific readiness via check_calculation_readiness() | DONE | CalculationType enum + CalculationReadinessResult; TAX_BASIS/HISTORICAL_RETURN/ANNUITY_INCOME/COST_ANALYSIS |
| R-38 | AnnuityTerms rate fields non-negative at model level | DONE | payout_rate, guaranteed_interest_rate, withdrawal_rate, surrender_period_years >= 0 |
| R-39 | FeeStructure all fee fields non-negative at model level | DONE | expense_ratio, advisory_fee_annual, exit_cost_pct, entry_cost_pct, other_one_time, other_recurring >= 0 |

## Open / Partial items for Day 2+

| ID | Item |
|----|------|
| R-17 | Allocation weight per-holding field and sum-to-1 validation |
| — | Tax engine implementation |
| — | Cost engine implementation |
| — | Performance engine implementation (requires historical data source) |
| — | Retirement engine implementation |
| — | Decision engine implementation |
| — | AI orchestration layer |
| — | Reporting / output layer |
| — | Resolve all 20 UNRESOLVED assumptions before engine runs |
