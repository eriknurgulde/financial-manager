"""Immutable domain entities.

Every entity is a frozen dataclass, so an "update" can only ever produce a new
value - there is no way to mutate an existing one. That property is what lets
the rest of `core` stay purely functional: a function can accept a
``tuple[Transaction, ...]`` and be certain nobody, anywhere, can change it
underneath.

Money is stored as an ``int`` in minor units (tiins for KZT) to avoid the
rounding drift that floats introduce when you sum thousands of transactions.
Income is positive, expense is negative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CategoryType = Literal["income", "expense"]
BudgetPeriod = Literal["month", "week"]

#: Event names published by the application (used from Lab 6 onwards).
TRANSACTION_ADDED = "TRANSACTION_ADDED"
OVER_BUDGET = "OVER_BUDGET"
BALANCE_ALERT = "BALANCE_ALERT"


@dataclass(frozen=True)
class Account:
    """A place where money sits: a card, a cash wallet, a savings account."""

    id: str
    name: str
    balance: int
    currency: str


@dataclass(frozen=True)
class Category:
    """A node in the category tree.

    ``parent_id is None`` marks a root category. The hierarchy itself is walked
    recursively in Lab 2; here it is only data.
    """

    id: str
    name: str
    parent_id: str | None
    type: CategoryType


@dataclass(frozen=True)
class Transaction:
    """A single money movement. Income is ``amount > 0``, expense ``amount < 0``."""

    id: str
    account_id: str
    cat_id: str
    amount: int
    ts: str
    note: str


@dataclass(frozen=True)
class Budget:
    """A spending limit for one category over one period.

    ``limit`` is a positive number: it is compared against the *magnitude* of
    the expenses in that category.
    """

    id: str
    cat_id: str
    limit: int
    period: BudgetPeriod


@dataclass(frozen=True)
class Event:
    """Something worth reacting to. Consumed by the event bus in Lab 6."""

    id: str
    ts: str
    name: str
    payload: dict


__all__ = [
    "BALANCE_ALERT",
    "OVER_BUDGET",
    "TRANSACTION_ADDED",
    "Account",
    "Budget",
    "BudgetPeriod",
    "Category",
    "CategoryType",
    "Event",
    "Transaction",
]
