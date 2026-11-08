"""Tax engine contract.

The tax engine must:
- Accept explicit tax rates (never invent or default them).
- Distinguish account types: TAXABLE_BROKERAGE, TRADITIONAL_IRA, ROTH_IRA, ANNUITY.
- Raise UnsupportedCalculationError if required rates are missing.
- Never conflate nominal and real values.
- Return gross and net tax liability separately.

This module contains Protocol definitions only — no implementations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol

from lpl.models.account import AccountType
from lpl.models.holding import Holding
from lpl.models.assumptions import AssumptionsRegister


class TaxRates(Protocol):
    """Tax rates provided by the advisor or derived from client data.

    These must be supplied explicitly — never hardcoded or invented.
    """

    @property
    def federal_ordinary_income_rate(self) -> Optional[Decimal]:
        """Federal marginal ordinary income tax rate. None = unknown."""
        ...

    @property
    def federal_long_term_cg_rate(self) -> Optional[Decimal]:
        """Federal long-term capital gains rate. None = unknown."""
        ...

    @property
    def state_income_rate(self) -> Optional[Decimal]:
        """State marginal income tax rate. None = unknown or N/A."""
        ...

    @property
    def niit_rate(self) -> Optional[Decimal]:
        """Net Investment Income Tax rate (3.8% if applicable). None = unknown."""
        ...


class TaxEngineInput(Protocol):
    """Input to the tax calculation engine."""

    @property
    def holding(self) -> Holding:
        """The holding being sold or converted."""
        ...

    @property
    def account_type(self) -> AccountType:
        """Account type — determines tax treatment."""
        ...

    @property
    def proceeds(self) -> Decimal:
        """Expected proceeds from the sale or conversion (nominal USD)."""
        ...

    @property
    def tax_rates(self) -> TaxRates:
        """Explicit tax rates — must not be None for calculations to proceed."""
        ...

    @property
    def assumptions(self) -> AssumptionsRegister:
        """Assumptions register for this calculation."""
        ...


class TaxEngineOutput(Protocol):
    """Output from the tax calculation engine."""

    @property
    def gross_proceeds(self) -> Decimal:
        """Proceeds before tax (nominal USD)."""
        ...

    @property
    def estimated_tax_liability(self) -> Optional[Decimal]:
        """Estimated tax due. None if calculation was not supported."""
        ...

    @property
    def net_proceeds(self) -> Optional[Decimal]:
        """After-tax proceeds. None if tax liability could not be computed."""
        ...

    @property
    def is_supported(self) -> bool:
        """False if any required input was missing; engine could not compute."""
        ...

    @property
    def unsupported_reason(self) -> Optional[str]:
        """Human-readable reason if is_supported is False."""
        ...


class TaxEngine(Protocol):
    """Interface for the tax calculation engine."""

    def calculate(self, input: TaxEngineInput) -> TaxEngineOutput:
        """Calculate tax liability for a sale or conversion.

        Must raise UnsupportedCalculationError if required rates are missing,
        rather than defaulting or approximating.
        """
        ...
