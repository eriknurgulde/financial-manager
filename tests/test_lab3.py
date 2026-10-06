# Tests for Lab 3. Run them with: pytest -q

from core.domain import Transaction
from core.memo import forecast_expenses, measure_forecast

TRANS = (
    Transaction("t1", "a1", "food", -100, "2026-09-01", "Milk"),
    Transaction("t2", "a1", "food", -50, "2026-09-02", "Coffee"),
    Transaction("t3", "a1", "transport", -30, "2026-09-03", "Bus"),
    Transaction("t4", "a1", "food", 500, "2026-09-04", "Refund"),
)


def test_forecast_expenses_average_per_period():
    # food expenses: 100 + 50 = 150, over 3 periods -> 50 per period.
    assert forecast_expenses("food", TRANS, 3) == 50


def test_forecast_expenses_ignores_income():
    # the +500 refund on "food" must not count as an expense.
    assert forecast_expenses("food", TRANS, 1) == 150


def test_forecast_expenses_unknown_category_is_zero():
    assert forecast_expenses("nope", TRANS, 3) == 0


def test_forecast_expenses_zero_period_is_zero():
    # avoid division by zero: period 0 gives forecast 0.
    assert forecast_expenses("food", TRANS, 0) == 0


def test_forecast_expenses_uses_cache():
    forecast_expenses.cache_clear()
    forecast_expenses("transport", TRANS, 1)
    forecast_expenses("transport", TRANS, 1)
    # same arguments twice -> second call is a cache hit.
    assert forecast_expenses.cache_info().hits == 1


def test_measure_forecast_returns_same_result_both_times():
    result, before_ms, after_ms = measure_forecast("food", TRANS, 3)
    assert result == 50
    assert before_ms >= 0
    assert after_ms >= 0
