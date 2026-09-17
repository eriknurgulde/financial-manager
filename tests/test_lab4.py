# Tests for Lab 4. Run them with: pytest -q

from core.domain import Account, Budget, Category, Transaction
from core.ftypes import Either, Maybe, check_budget, safe_category, validate_transaction

ACCS = (Account("a1", "Card", 100000, "KZT"),)
CATS = (Category("food", "Food", None, "expense"),)
BUDGET = Budget("b1", "food", 200, "month")


def test_maybe_map_on_some():
    assert Maybe.some(2).map(lambda x: x + 1).get_or_else(0) == 3


def test_maybe_map_on_nothing_stays_nothing():
    assert Maybe.nothing().map(lambda x: x + 1).get_or_else(0) == 0


def test_maybe_bind_chains_two_maybes():
    half = lambda x: Maybe.some(x / 2) if x % 2 == 0 else Maybe.nothing()
    assert Maybe.some(4).bind(half).get_or_else(-1) == 2
    assert Maybe.some(3).bind(half).get_or_else(-1) == -1


def test_either_map_on_right():
    assert Either.right_of(2).map(lambda x: x * 10).get_or_else(0) == 20


def test_either_map_on_left_keeps_error():
    err = Either.left_of("bad").map(lambda x: x * 10)
    assert err.is_right is False
    assert err.left == "bad"


def test_safe_category_found_and_missing():
    assert safe_category(CATS, "food").has_value is True
    assert safe_category(CATS, "nope").has_value is False


def test_validate_transaction_rejects_unknown_account():
    t = Transaction("t1", "no_acc", "food", -50, "2026-09-01", "x")
    result = validate_transaction(t, ACCS, CATS)
    assert result.is_right is False
    assert result.left["error"] == "account not found"


def test_validate_transaction_rejects_unknown_category():
    t = Transaction("t1", "a1", "no_cat", -50, "2026-09-01", "x")
    result = validate_transaction(t, ACCS, CATS)
    assert result.is_right is False
    assert result.left["error"] == "category not found"


def test_validate_transaction_accepts_good_transaction():
    t = Transaction("t1", "a1", "food", -50, "2026-09-01", "x")
    assert validate_transaction(t, ACCS, CATS).is_right is True


def test_check_budget_within_and_exceeded():
    trans = (Transaction("t1", "a1", "food", -100, "2026-09-01", "x"),)
    assert check_budget(BUDGET, trans).is_right is True

    over_trans = (Transaction("t2", "a1", "food", -300, "2026-09-01", "x"),)
    over = check_budget(BUDGET, over_trans)
    assert over.is_right is False
    assert over.left["error"] == "budget exceeded"
