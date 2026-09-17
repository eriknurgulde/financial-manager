# Tests for Lab 2. Run them with: pytest -q

from core.domain import Category, Transaction
from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import by_amount_range, by_category, by_date_range

# Small category tree: food -> groceries, cafe
CATS = (
    Category("food", "Food", None, "expense"),
    Category("groceries", "Groceries", "food", "expense"),
    Category("cafe", "Cafe", "food", "expense"),
    Category("transport", "Transport", None, "expense"),
)
TRANS = (
    Transaction("t1", "a1", "groceries", -100, "2026-09-01", "Milk"),
    Transaction("t2", "a1", "cafe", -50, "2026-09-02", "Coffee"),
    Transaction("t3", "a1", "transport", -30, "2026-09-03", "Bus"),
    Transaction("t4", "a1", "food", 500, "2026-09-04", "Refund"),
)


def test_by_category_closure():
    is_cafe = by_category("cafe")
    assert is_cafe(TRANS[1]) is True
    assert is_cafe(TRANS[0]) is False


def test_by_date_range_closure():
    in_range = by_date_range("2026-09-02", "2026-09-03")
    assert in_range(TRANS[1]) is True  # 09-02
    assert in_range(TRANS[0]) is False  # 09-01, before start


def test_by_amount_range_closure():
    small = by_amount_range(-60, -1)
    assert small(TRANS[1]) is True  # -50
    assert small(TRANS[0]) is False  # -100, too big


def test_flatten_categories_includes_root_and_children():
    result = flatten_categories(CATS, "food")
    ids = {c.id for c in result}
    assert ids == {"food", "groceries", "cafe"}


def test_flatten_categories_leaf_has_no_children():
    result = flatten_categories(CATS, "transport")
    assert result == (CATS[3],)


def test_sum_expenses_recursive_sums_children():
    # groceries -100, cafe -50 -> 150. The +500 income row is ignored.
    assert sum_expenses_recursive(CATS, TRANS, "food") == 150


def test_sum_expenses_recursive_unknown_root_is_zero():
    assert sum_expenses_recursive(CATS, TRANS, "nope") == 0
