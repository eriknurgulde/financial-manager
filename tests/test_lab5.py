# Tests for Lab 5. Run them with: pytest -q

import inspect

from core.domain import Category, Transaction
from core.lazy import iter_transactions, lazy_top_categories

CATS = (
    Category("food", "Food", None, "expense"),
    Category("transport", "Transport", None, "expense"),
)

TRANS = (
    Transaction("t1", "a1", "food", -100, "2026-09-01", "x"),
    Transaction("t2", "a1", "food", -300, "2026-09-02", "x"),
    Transaction("t3", "a1", "transport", -50, "2026-09-03", "x"),
    Transaction("t4", "a1", "food", 1000, "2026-09-04", "income"),
)


def test_iter_transactions_is_a_generator():
    result = iter_transactions(TRANS, lambda t: True)
    assert inspect.isgenerator(result)


def test_iter_transactions_filters_by_pred():
    found = list(iter_transactions(TRANS, lambda t: t.cat_id == "food"))
    assert [t.id for t in found] == ["t1", "t2", "t4"]


def test_iter_transactions_yields_nothing_matched():
    found = list(iter_transactions(TRANS, lambda t: t.cat_id == "no_cat"))
    assert found == []


def test_lazy_top_categories_is_a_generator():
    result = lazy_top_categories(iter(TRANS), CATS, 2)
    assert inspect.isgenerator(result)


def test_lazy_top_categories_orders_by_spent_desc():
    top = list(lazy_top_categories(iter(TRANS), CATS, 2))
    assert top == [("Food", 400), ("Transport", 50)]


def test_lazy_top_categories_respects_k():
    top = list(lazy_top_categories(iter(TRANS), CATS, 1))
    assert top == [("Food", 400)]


def test_lazy_pipeline_together():
    # iter_transactions -> lazy_top_categories, both lazy until list().
    expenses = iter_transactions(TRANS, lambda t: t.amount < 0)
    top = list(lazy_top_categories(expenses, CATS, 5))
    assert ("Food", 400) in top
    assert ("Transport", 50) in top
