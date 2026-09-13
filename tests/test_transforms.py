"""Tests for the pure functional core."""

import copy

import pytest

from core.domain import Account, Budget, Category, Transaction
from core.transforms import (
    account_balance,
    add_transaction,
    current_balance,
    expenses_by_category,
    find_account,
    find_budget,
    find_category,
    format_money,
    overview,
    sum_amounts,
    total_balance,
    total_expenses,
    total_income,
    update_budget,
    where,
)

ACCOUNTS = (
    Account(id="a1", name="Card", balance=100_000, currency="KZT"),
    Account(id="a2", name="Cash", balance=50_000, currency="KZT"),
)

CATEGORIES = (
    Category(id="c_food", name="Food", parent_id=None, type="expense"),
    Category(id="c_food_cafe", name="Cafes", parent_id="c_food", type="expense"),
    Category(id="c_salary", name="Salary", parent_id=None, type="income"),
)


def tx(tid, acc, cat, amount, ts="2026-09-01T12:00:00", note=""):
    return Transaction(
        id=tid, account_id=acc, cat_id=cat, amount=amount, ts=ts, note=note
    )


TRANS = (
    tx("t1", "a1", "c_salary", 400_000),
    tx("t2", "a1", "c_food", -25_000),
    tx("t3", "a1", "c_food_cafe", -15_000),
    tx("t4", "a2", "c_food", -10_000),
)

BUDGETS = (
    Budget(id="b1", cat_id="c_food", limit=100_000, period="month"),
    Budget(id="b2", cat_id="c_food_cafe", limit=30_000, period="week"),
)


# --------------------------------------------------------------------------
# add_transaction
# --------------------------------------------------------------------------


def test_add_transaction_returns_a_new_tuple_with_the_item_appended():
    new_tx = tx("t5", "a2", "c_food", -1_000)

    result = add_transaction(TRANS, new_tx)

    assert result == (*TRANS, new_tx)
    assert isinstance(result, tuple)


def test_add_transaction_does_not_touch_the_input():
    before = TRANS

    add_transaction(TRANS, tx("t5", "a2", "c_food", -1_000))

    assert before == TRANS
    assert len(TRANS) == 4


def test_add_transaction_onto_an_empty_log():
    only = tx("t1", "a1", "c_food", -100)

    assert add_transaction((), only) == (only,)


# --------------------------------------------------------------------------
# update_budget
# --------------------------------------------------------------------------


def test_update_budget_replaces_only_the_matching_budget():
    result = update_budget(BUDGETS, "b1", 250_000)

    assert result[0].limit == 250_000
    assert result[0].id == "b1"
    assert result[1] == BUDGETS[1], "the other budget must be untouched"


def test_update_budget_leaves_the_original_tuple_alone():
    update_budget(BUDGETS, "b1", 250_000)

    assert BUDGETS[0].limit == 100_000


def test_update_budget_with_an_unknown_id_returns_an_equal_tuple():
    result = update_budget(BUDGETS, "does-not-exist", 1)

    assert result == BUDGETS


def test_update_budget_preserves_order_and_length():
    result = update_budget(BUDGETS, "b2", 1)

    assert [b.id for b in result] == ["b1", "b2"]


# --------------------------------------------------------------------------
# account_balance  (reduce)
# --------------------------------------------------------------------------


def test_account_balance_sums_only_that_accounts_transactions():
    # a1: +400_000 - 25_000 - 15_000
    assert account_balance(TRANS, "a1") == 360_000
    assert account_balance(TRANS, "a2") == -10_000


def test_account_balance_of_an_unknown_account_is_zero():
    assert account_balance(TRANS, "nope") == 0


def test_account_balance_of_an_empty_log_is_zero():
    assert account_balance((), "a1") == 0


def test_current_balance_adds_the_opening_balance():
    assert current_balance(ACCOUNTS[0], TRANS) == 100_000 + 360_000
    assert current_balance(ACCOUNTS[1], TRANS) == 50_000 - 10_000


def test_total_balance_covers_every_account():
    assert total_balance(ACCOUNTS, TRANS) == 460_000 + 40_000


# --------------------------------------------------------------------------
# aggregates
# --------------------------------------------------------------------------


def test_total_income_and_expenses_are_reported_as_magnitudes():
    assert total_income(TRANS) == 400_000
    assert total_expenses(TRANS) == 50_000


def test_totals_of_an_empty_log_are_zero():
    assert total_income(()) == 0
    assert total_expenses(()) == 0
    assert sum_amounts(()) == 0


def test_expenses_by_category_groups_direct_hits_only():
    result = expenses_by_category(TRANS)

    assert result == {"c_food": 35_000, "c_food_cafe": 15_000}
    assert "c_salary" not in result, "income is not an expense"


def test_expenses_by_category_does_not_roll_children_into_the_parent():
    # Rolling c_food_cafe up into c_food is Lab 2's recursive job.
    result = expenses_by_category(TRANS)

    assert result["c_food"] == 35_000


def test_overview_reports_the_four_headline_numbers():
    result = overview(ACCOUNTS, CATEGORIES, TRANS)

    assert result["accounts"] == 2
    assert result["categories"] == 3
    assert result["transactions"] == 4
    assert result["total_balance"] == 500_000


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def test_where_filters_with_an_arbitrary_predicate():
    result = where(TRANS, lambda t: t.amount < -12_000)

    assert [t.id for t in result] == ["t2", "t3"]
    assert isinstance(result, tuple)


def test_finders_return_the_match_or_none():
    assert find_account(ACCOUNTS, "a2").name == "Cash"
    assert find_account(ACCOUNTS, "zzz") is None
    assert find_category(CATEGORIES, "c_food").name == "Food"
    assert find_category(CATEGORIES, "zzz") is None
    assert find_budget(BUDGETS, "b2").period == "week"
    assert find_budget(BUDGETS, "zzz") is None


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "0.00 KZT"),
        (450_000, "4 500.00 KZT"),
        (-450_000, "-4 500.00 KZT"),
        (1, "0.01 KZT"),
        (123_456_789, "1 234 567.89 KZT"),
    ],
)
def test_format_money_renders_minor_units(amount, expected):
    assert format_money(amount) == expected


def test_the_whole_core_leaves_its_inputs_untouched():
    """One sweep: call everything, then check nothing moved.

    The snapshots are deep copies, so this compares against independent objects
    rather than re-checking the same tuple against itself.
    """
    accounts_before = copy.deepcopy(ACCOUNTS)
    trans_before = copy.deepcopy(TRANS)
    budgets_before = copy.deepcopy(BUDGETS)

    add_transaction(TRANS, tx("t9", "a1", "c_food", -1))
    update_budget(BUDGETS, "b1", 999)
    account_balance(TRANS, "a1")
    total_balance(ACCOUNTS, TRANS)
    expenses_by_category(TRANS)
    where(TRANS, lambda t: t.amount != 0)

    assert accounts_before == ACCOUNTS
    assert trans_before == TRANS
    assert budgets_before == BUDGETS
