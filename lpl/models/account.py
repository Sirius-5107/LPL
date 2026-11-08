"""Account model and account-type taxonomy.

Traditional IRA, Roth IRA, taxable brokerage, and annuity accounts have
fundamentally different tax treatments and must never be treated as equivalent.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field


class AccountType(str, Enum):
    """Tax and legal classification of an account.

    These are NOT interchangeable. Tax calculations must branch on this enum.
    - TAXABLE_BROKERAGE: realized gains taxed; cost basis tracking required.
    - TRADITIONAL_IRA:   pre-tax contributions; withdrawals taxed as ordinary income.
    - ROTH_IRA:          after-tax contributions; qualified withdrawals tax-free.
    - ANNUITY:           insurance contract; tax treatment depends on contract type.
    - UNKNOWN:           not yet determined; must be resolved before tax calculations.
    """

    TAXABLE_BROKERAGE = "taxable_brokerage"
    TRADITIONAL_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    ANNUITY = "annuity"
    UNKNOWN = "unknown"


class Account(BaseModel):
    """An investment account with a specific tax classification.

    Fields
    ------
    account_id:   Unique identifier for this account.
    account_type: Tax/legal classification. Must not be UNKNOWN for calculations.
    label:        Human-readable label, e.g. "Vanguard annuity".
    custodian:    Institution holding the account, if known.
    notes:        Any unresolved or contextual information.
    """

    account_id: str
    account_type: AccountType
    label: str
    custodian: Optional[str] = None
    notes: Optional[str] = None
