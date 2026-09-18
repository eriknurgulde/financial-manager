# Tests for Lab 1. Run them with: pytest -q

import dataclasses

import pytest

from core.domain import Account, Budget, Transaction
from core.transforms import (
    account_balance,
    add_transaction,
    load_seed,
    total_balance,
    update_budget,
)

# Small test data that is easy to count by hand.
ACCOUNTS = (Account("a1", "Card", 1000, "KZT"),)
TRANS = (
    Transaction("t1", "a1", "salary", 500, "2026-09-01", "Salary"),
    Transaction("t2", "a1", "cafe", -200, "2026-09-02", "Lunch"),
    Transaction("t3", "a2", "cafe", -50, "2026-09-03", "Coffee"),
)
BUDGETS = (
    Budget("b1", "food", 100, "month"),
    Budget("b2", "taxi", 50, "month"),
)


def test_models_are_immutable():
    # Changing a field of a frozen object must raise an error.
    with pytest.raises(dataclasses.FrozenInstanceError):
        ACCOUNTS[0].balance = 0


def test_add_transaction_returns_new_tuple():
    new_t = Transaction("t4", "a1", "cafe", -10, "2026-09-04", "Tea")
    result = add_transaction(TRANS, new_t)
    assert len(result) == 4  # the new tuple has one more item
    assert len(TRANS) == 3  # the old tuple did not change


def test_update_budget_changes_only_one_budget():
    result = update_budget(BUDGETS, "b1", 999)
    assert result[0].limit == 999  # b1 got the new limit
    assert result[1].limit == 50  # b2 stayed the same
    assert BUDGETS[0].limit == 100  # the old tuple did not change


def test_account_balance():
    # a1: +500 - 200 = 300. The a2 transaction is not counted.
    assert account_balance(TRANS, "a1") == 300


def test_account_balance_unknown_account_is_zero():
    assert account_balance(TRANS, "nope") == 0


def test_total_balance():
    # start balance 1000 + transactions of a1 (300) = 1300
    assert total_balance(ACCOUNTS, TRANS) == 1300


def test_load_seed_has_enough_data():
    # The task asks for: 3+ accounts, 10+ categories,
    # 100+ transactions and 3+ budgets.
    accounts, categories, transactions, budgets = load_seed("data/seed.json")
    assert len(accounts) >= 3
    assert len(categories) >= 10
    assert len(transactions) >= 100
    assert len(budgets) >= 3
