"""Client model — demographic, goal, and constraint information."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from lpl.models.portfolio import Portfolio


class ClientGoals(BaseModel):
    """Client financial goals.

    Fields
    ------
    target_retirement_age:   Age at which the client intends to retire.
    target_monthly_income:   Desired monthly income in retirement (nominal USD).
    legacy_target:           Desired bequest value in nominal USD, if any.
    notes:                   Any unresolved or context notes.
    """

    target_retirement_age: Optional[int] = None
    target_monthly_income: Optional[Decimal] = None
    legacy_target: Optional[Decimal] = None
    notes: Optional[str] = None


class ClientConstraints(BaseModel):
    """Client constraints that must be respected by transition logic.

    Fields
    ------
    tax_filing_status:    e.g. "single", "married_filing_jointly". None = unknown.
    state_of_residence:   Two-letter state code for state tax purposes.
    risk_tolerance:       Self-reported risk tolerance label.
    liquidity_need_years: Minimum years of liquidity the client must maintain.
    notes:                Any unresolved or context notes.
    """

    tax_filing_status: Optional[str] = None
    state_of_residence: Optional[str] = None
    risk_tolerance: Optional[str] = None
    liquidity_need_years: Optional[int] = None
    notes: Optional[str] = None


class Client(BaseModel):
    """An advisor's client whose portfolio is under analysis.

    The reference client must be loadable from a JSON file without any
    hardcoding in business logic. A second client must be loadable by
    providing a different file path.

    Fields
    ------
    client_id:         Unique identifier (not a real SSN or account number).
    name:              Client name or pseudonym.
    age:               Current age in years.
    goals:             Financial goals.
    constraints:       Constraints and preferences.
    ci_portfolio:      Current Investment Portfolio.
    pi_portfolio:      Proposed Investment Portfolio (may be None if not yet built).
    ri_portfolio:      Independently Recommended Portfolio (optional).
    notes:             Unresolved items or context.
    """

    client_id: str
    name: str
    age: Optional[int] = None
    goals: ClientGoals = Field(default_factory=ClientGoals)
    constraints: ClientConstraints = Field(default_factory=ClientConstraints)
    ci_portfolio: Portfolio
    pi_portfolio: Optional[Portfolio] = None
    ri_portfolio: Optional[Portfolio] = None
    notes: Optional[str] = None
