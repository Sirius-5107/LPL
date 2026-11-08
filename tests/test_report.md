# Test Report — Day 1

**Run date:** 2026-11-09  
**Python:** 3.13.18  
**pytest:** 9.1.1  
**Platform:** Linux

## Results

```
45 passed in 0.06s
```

## Breakdown

| File | Tests | Passed | Failed |
|------|-------|--------|--------|
| tests/test_loaders.py | 18 | 18 | 0 |
| tests/test_models.py | 17 | 17 | 0 |
| tests/test_validation.py | 10 | 10 | 0 |
| **Total** | **45** | **45** | **0** |

## Coverage by rule

| Design rule | Test(s) |
|-------------|---------|
| Missing cost basis is None, not zero | test_holding_unknown_cost_basis_is_none, test_ci_annuity_cost_basis_unknown |
| cost_basis and cost_basis_status must be consistent | test_holding_cost_basis_consistency_error, test_holding_cost_basis_known_but_none_raises |
| Annuity rate fields are distinct and not conflated | test_annuity_terms_unresolved, test_annuity_terms_distinct_fields |
| One-time vs recurring fees are separate fields | test_fee_structure_one_time_vs_recurring |
| CI and PI have different portfolio IDs and labels | test_ci_pi_different_ids, test_ci_pi_same_id_raises |
| Illiquid assets blocked from transition instructions | test_illiquid_transition_blocked, test_illiquid_retain_is_ok |
| Portfolio total reconciles | test_portfolio_reconciles_ok, test_portfolio_reconciliation_fails |
| Unknown cost basis flagged as warning (not error) | test_unknown_cost_basis_flagged |
| Reference client loads from JSON without hardcoding | test_reference_client_loads, test_second_client_loadable |
| No fabricated tax rates or missing data | test_no_tax_rates_fabricated, test_missing_data_explicit_nulls |
| Traditional IRA account type correctly set | test_ci_traditional_ira |
| Real estate is illiquid | test_ci_real_estate_illiquid |
| Alternatives are partially liquid | test_ci_alternatives_partially_liquid |
| PI has Roth IRA | test_pi_has_roth_ira |
