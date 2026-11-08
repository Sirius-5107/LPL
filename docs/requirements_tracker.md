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
| R-17 | Allocation weight validation | PARTIAL | Validation infrastructure exists; weight field not yet modelled on Portfolio |
| R-18 | Illiquid constraint in transition validation | DONE | validate_transition_instructions() |
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
