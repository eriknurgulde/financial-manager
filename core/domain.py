# Data models of the app.
# frozen=True makes every object read-only: after it is created,
# nobody can change its fields. This is the "immutable data" rule.

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    # A bank card or a wallet. balance is the start money in tenge.
    id: str
    name: str
    balance: int
    currency: str


@dataclass(frozen=True)
class Category:
    # A group of spending, like "Food".
    # parent_id is None for a main category, or the id of its parent.
    # type is "income" or "expense".
    id: str
    name: str
    parent_id: str | None
    type: str


@dataclass(frozen=True)
class Transaction:
    # One money operation.
    # amount > 0 means income, amount < 0 means expense.
    id: str
    account_id: str
    cat_id: str
    amount: int
    ts: str
    note: str


@dataclass(frozen=True)
class Budget:
    # A spending limit for one category. period is "month" or "week".
    id: str
    cat_id: str
    limit: int
    period: str


@dataclass(frozen=True)
class Event:
    # Something that happened in the app (used in later labs).
    id: str
    ts: str
    name: str
    payload: dict
