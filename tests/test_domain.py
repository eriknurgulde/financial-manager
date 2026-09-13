"""Tests for the immutability guarantees of the domain entities."""

import dataclasses

import pytest

from core.domain import Account, Budget, Category, Event, Transaction


def test_account_is_frozen():
    acc = Account(id="a1", name="Kaspi Gold", balance=250_000, currency="KZT")

    with pytest.raises(dataclasses.FrozenInstanceError):
        acc.balance = 999


@pytest.mark.parametrize(
    "entity",
    [
        Account(id="a1", name="Cash", balance=0, currency="KZT"),
        Category(id="c1", name="Food", parent_id=None, type="expense"),
        Transaction(id="t1", account_id="a1", cat_id="c1", amount=-500, ts="", note=""),
        Budget(id="b1", cat_id="c1", limit=100, period="month"),
        Event(id="e1", ts="", name="TRANSACTION_ADDED", payload={}),
    ],
)
def test_every_entity_rejects_mutation(entity):
    field = dataclasses.fields(entity)[0].name

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(entity, field, "mutated")


def test_replace_returns_a_new_object_and_leaves_the_original_alone():
    original = Budget(id="b1", cat_id="c_food", limit=100_000, period="month")

    updated = dataclasses.replace(original, limit=150_000)

    assert updated is not original
    assert updated.limit == 150_000
    assert original.limit == 100_000, "the input value must not be touched"


def test_entities_compare_by_value_not_identity():
    left = Category(id="c1", name="Food", parent_id=None, type="expense")
    right = Category(id="c1", name="Food", parent_id=None, type="expense")

    assert left == right
    assert left is not right


def test_income_is_positive_and_expense_is_negative():
    income = Transaction(
        id="t1",
        account_id="a1",
        cat_id="c_salary",
        amount=800_000,
        ts="2026-09-01T10:00:00",
        note="September salary",
    )
    expense = Transaction(
        id="t2",
        account_id="a1",
        cat_id="c_food",
        amount=-4_500,
        ts="2026-09-01T13:20:00",
        note="Lunch",
    )

    assert income.amount > 0
    assert expense.amount < 0


def test_root_category_has_no_parent_and_child_points_at_it():
    root = Category(id="c_food", name="Food", parent_id=None, type="expense")
    child = Category(id="c_food_cafe", name="Cafes", parent_id="c_food", type="expense")

    assert root.parent_id is None
    assert child.parent_id == root.id


def test_hashable_entities_can_live_in_a_set():
    a = Account(id="a1", name="Cash", balance=0, currency="KZT")
    same = Account(id="a1", name="Cash", balance=0, currency="KZT")
    other = Account(id="a2", name="Card", balance=10, currency="KZT")

    assert len({a, same, other}) == 2


def test_frozen_entities_reject_brand_new_attributes_too():
    acc = Account(id="a1", name="Cash", balance=0, currency="KZT")

    with pytest.raises(dataclasses.FrozenInstanceError):
        acc.nickname = "piggy bank"
