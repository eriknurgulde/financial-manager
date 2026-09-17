# Pure functions for Lab 1.
# A pure function only uses its inputs and returns a result.
# It never changes the data it gets - it builds and returns new data.

import json
from dataclasses import replace
from functools import reduce

from core.domain import Account, Budget, Category, Transaction


def load_seed(path: str) -> tuple:
    # Read the JSON file and turn every record into a model object.
    # We return tuples, because a tuple cannot be changed.
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    accounts = tuple(map(lambda a: Account(**a), data["accounts"]))
    categories = tuple(map(lambda c: Category(**c), data["categories"]))
    transactions = tuple(map(lambda t: Transaction(**t), data["transactions"]))
    budgets = tuple(map(lambda b: Budget(**b), data["budgets"]))
    return accounts, categories, transactions, budgets


def add_transaction(
    trans: tuple[Transaction, ...], t: Transaction
) -> tuple[Transaction, ...]:
    # Return a NEW tuple: all old transactions plus the new one.
    # The old tuple stays the same.
    return trans + (t,)


def update_budget(
    budgets: tuple[Budget, ...], bid: str, new_limit: int
) -> tuple[Budget, ...]:
    # Go through all budgets with map.
    # The budget with id == bid is copied with the new limit (replace).
    # All other budgets are kept as they are.
    return tuple(
        map(lambda b: replace(b, limit=new_limit) if b.id == bid else b, budgets)
    )


def account_balance(trans: tuple[Transaction, ...], acc_id: str) -> int:
    # 1) filter: keep only transactions of this account
    # 2) map: take the amount of each transaction
    # 3) reduce: add all amounts together (start from 0)
    # Expenses are negative numbers, so a simple sum is enough.
    own = filter(lambda t: t.account_id == acc_id, trans)
    amounts = map(lambda t: t.amount, own)
    return reduce(lambda total, x: total + x, amounts, 0)


def total_balance(accounts: tuple[Account, ...], trans: tuple[Transaction, ...]) -> int:
    # Money on all accounts together:
    # start balance of each account + all its transactions.
    return reduce(
        lambda total, a: total + a.balance + account_balance(trans, a.id),
        accounts,
        0,
    )


# --- Closures (Lab 2) ---
# A closure is a function that "remembers" the values from its outer
# function. Each function below builds and returns a small filter
# function that keeps that memory (cat_id, start/end, min/max).


def by_category(cat_id: str):
    # Returns a filter: keep only transactions of one category.
    return lambda t: t.cat_id == cat_id


def by_date_range(start: str, end: str):
    # Returns a filter: keep only transactions inside [start, end].
    # Dates are text like "2026-06-01", so normal text compare works.
    return lambda t: start <= t.ts <= end


def by_amount_range(min: int, max: int):
    # Returns a filter: keep only transactions with amount in [min, max].
    return lambda t: min <= t.amount <= max
