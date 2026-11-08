# LPL Financial — Advisor Investment Transition Decision-Support System

Inter IIT Tech Meet 15.0

---

## Setup

**Requirements:** Python 3.11+

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Run tests

```
pytest tests/ -v
# Expected: 45 passed
```

## Load the reference client

```python
from lpl.loaders.client_loader import load_client_from_json

client = load_client_from_json("data/clients/reference_client.json")
print(client.ci_portfolio.total_market_value)  # Decimal('700000')
```

## Load a second client (no source changes needed)

```python
client2 = load_client_from_json("data/clients/my_other_client.json")
```

## Validate a portfolio

```python
from lpl.validation.validators import validate_portfolio, validate_ci_pi_separation

report = validate_portfolio(client.ci_portfolio)
print(report.errors())    # Must be empty before calculations
print(report.warnings())  # Missing cost basis etc.

sep_report = validate_ci_pi_separation(client.ci_portfolio, client.pi_portfolio)
```

## Project structure

```
lpl/                  Python package
  models/             Pydantic data models
  validation/         Validation rules → ValidationReport
  contracts/          Typed Protocol interfaces for engines (no implementations)
  loaders/            Load Client from JSON file
  exceptions.py       Domain exceptions

data/clients/         Client JSON files (never hardcoded)
docs/                 Architecture, data dictionary, assumptions register, requirements
tests/                pytest tests
```

## Documentation

- [Architecture](docs/architecture.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Assumptions Register](docs/assumptions_register.md)
- [Requirements Tracker](docs/requirements_tracker.md)
- [Test Report](tests/test_report.md)
