# Architecture — LPL Financial Advisor Transition Decision-Support System

**Version:** 0.1.0 (Day 1)  
**Status:** Foundation

---

## 1. Overview

The system is a **modular monolith** in Python 3.11+. All components live in a single
deployable package (`lpl/`), with strict internal module boundaries enforced by
import discipline and typed interfaces.

The fundamental separation is:

```
Deterministic financial layer  ←→  AI-assisted orchestration layer
```

The financial calculation layer is **fully deterministic**. Given identical inputs,
it produces identical outputs. It never calls an LLM or accept stochastic results as
financial figures.

The AI layer assists with intake, clarification of ambiguous dossier terms, retrieval,
explanation generation, and workflow orchestration. It **never** calculates, invent,
round, or modify financial figures.

---

## 2. Component map

```
lpl/
├── models/          Data models (Pydantic). Pure data, no logic.
├── validation/      Validation rules. Deterministic. Returns ValidationReport.
├── contracts/       Protocol interfaces for each calculation engine. No implementations.
├── loaders/         Load clients from JSON files. No hardcoding.
└── exceptions.py    Domain exceptions. Explicit, descriptive.

data/
└── clients/         Client JSON files. Reference client + any additional clients.

docs/                Architecture, data dictionary, assumptions register, requirements.
tests/               pytest tests. Must all pass before commit.
```

---

## 3. Module responsibilities

### models/
Pure Pydantic data models. No business logic. No calculations.
Models validate structural integrity (e.g. cost_basis consistency) but do not
compute tax or returns.

| Module | Key types |
|--------|-----------|
| account.py | Account, AccountType |
| holding.py | Holding, LiquidityStatus, CostBasisStatus, AssetClass |
| product.py | Investment, AnnuityTerms, FeeStructure, RateInterpretation |
| portfolio.py | Portfolio, PortfolioLabel, PortfolioSummary |
| client.py | Client, ClientGoals, ClientConstraints |
| transition.py | TransitionInstruction, TransitionAction, TransitionEligibility |
| scenario.py | Scenario, ScenarioType |
| assumptions.py | Assumption, AssumptionStatus, AssumptionsRegister |

### validation/
Stateless functions that accept models and return a `ValidationReport`.
Errors block calculations. Warnings must be reviewed. Validation never raises
directly — callers decide how to handle the report.

| Function | Purpose |
|----------|---------|
| `validate_portfolio()` | Reconciliation, cost basis warnings, account type checks. |
| `validate_ci_pi_separation()` | Ensures CI and PI have distinct IDs and labels. |
| `validate_transition_instructions()` | Enforces illiquid/restricted/fractional/CONVERT rules. |
| `validate_calculation_readiness()` | Reports missing or unresolved data that would block downstream engines. Does NOT calculate. |

### contracts/
Typed `Protocol` interfaces for each calculation engine. These define the
contract (inputs, outputs, method signatures) without any implementation.
Engines are implemented in later days and must satisfy these protocols.

| Contract | Engine responsibility |
|----------|-----------------------|
| tax.py | After-tax proceeds from sales and conversions |
| costs.py | One-time and recurring cost calculation |
| performance.py | Historical return, risk, and downside metrics |
| retirement.py | Retirement income projection (ages 60–90) |
| decision.py | Synthesis into a recommendation |

### loaders/
Thin I/O layer. Reads JSON, validates through Pydantic, returns a `Client`.
No business logic. A second client is loaded by passing a different path —
no source code changes required.

### exceptions.py
Domain exceptions that must be raised explicitly:
- `MissingCostBasisError` — cost basis accessed when it is UNKNOWN
- `IlliquidAssetTransitionError` — illiquid holding in a sell instruction
- `UnsupportedCalculationError` — required input missing; must not approximate
- `UnresolvedAnnuityTermsError` — annuity rate used before interpretation clarified
- `PortfolioReconciliationError` — holdings do not sum to declared total
- `CIandPIConflictError` — CI and PI share ID or label

---

## 4. Dependency flow

```
Client JSON file
      │
      ▼
   loaders/
      │  load_client_from_json()
      ▼
   models/        (Pydantic validation on load)
      │
      ▼
  validation/     (ValidationReport — errors and warnings)
      │
      ▼
  contracts/      (typed interfaces consumed by engine implementations)
      │
      ▼
  [Tax engine]  [Cost engine]  [Performance engine]  [Retirement engine]
      │               │                │                     │
      └───────────────┴────────────────┘─────────────────────┘
                                       │
                                       ▼
                               [Decision engine]
                                       │
                                       ▼
                                [Report / output]
```

The AI layer sits above this stack. It may:
- Help advisors answer clarifying questions about dossier inputs
- Translate unresolved assumption status into natural-language explanations
- Orchestrate the workflow (which engines to run, in what order)
- Explain recommendation rationale in plain language

It may NOT modify, compute, or round any financial figure.

---

## 5. Separation: deterministic calculations vs AI

| Deterministic layer | AI layer |
|---------------------|----------|
| Tax liability | Explain tax implications to advisor |
| Cost calculation | Summarise cost comparison |
| Retirement projection | Translate projection into plain language |
| Portfolio reconciliation | Flag and explain unresolved items |
| Validation report | Present validation issues to advisor |
| Recommendation outcome | Draft recommendation narrative |

---

## 6. Data flow

1. Advisor uploads client dossier (JSON or intake form)
2. `load_client_from_json()` parses and validates the client
3. `validate_portfolio()` checks reconciliation, cost basis, liquidity
4. `validate_ci_pi_separation()` ensures CI and PI are distinct
5. Scenario is constructed with transition instructions
6. `validate_transition_instructions()` checks illiquid and fraction rules
7. Engines (tax, costs, performance, retirement) compute outputs
8. `DecisionEngine.recommend()` synthesises into a recommendation
9. Report is generated and surfaced to the advisor

---

## 7. Major architectural risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Annuity rate terms are unresolved | HIGH | Rate fields are distinct; RateInterpretation.UNRESOLVED blocks rate-dependent calculations |
| Missing cost basis for 4 of 5 CI sleeves | HIGH | CostBasisStatus.UNKNOWN propagates explicitly; MissingCostBasisError raised if used |
| Traditional IRA → Roth conversion tax cost unknown | HIGH | Marked UNRESOLVED; conversion amount must be provided before tax engine runs |
| Real estate account type unconfirmed | MEDIUM | AccountType.UNKNOWN; tax engine must check and raise UnsupportedCalculationError |
| No tax rates in client dossier | HIGH | TaxRates fields are Optional; tax engine must raise if None when rates are needed |
| Alternatives sub-allocation unknown | MEDIUM | Sub-holdings list empty; individual cost basis cannot be computed |
| Retirement projection inputs incomplete | MEDIUM | RetirementEngine.is_supported = False when inputs absent |

---

## 8. Integration boundaries

Future integrations (not Day 1):
- **AI layer**: LLM calls for intake, clarification, explanation. Must not write to models.
- **Data providers**: Historical return data for performance engine.
- **Tax engine implementations**: Must satisfy `contracts/tax.py` Protocol.
- **Frontend**: Separate from this package entirely.
- **Persistence**: Client JSON files now; a database adapter can wrap `loaders/` later.

---

## 9. Decisions requiring team agreement

See `assumptions_register.md` for the full list. Key items:

1. What does "3% fixed lifetime income" (Vanguard annuity) mean economically?
2. What does "3.25%" (Fidelity annuity) mean economically?
3. What is the legal/tax structure of the real-estate fund of funds?
4. What is the Traditional IRA → Roth conversion amount?
5. What tax rates apply to this client?
6. What is the client's age, retirement target, and income goal?
7. What is the sub-allocation within the alternatives sleeve?
