# Tests for Lab 7. Run them with: pytest -q

from core.compose import compose, pipe
from core.domain import Budget, Transaction
from core.service import (
    BudgetService,
    ReportService,
    make_budget_validator,
    make_category_aggregator,
    make_spending_calculator,
)

BUDGETS = (Budget("b1", "food", 1000, "month"),)
TRANS = (
    Transaction("t1", "a1", "food", -300, "2026-09-01", "x"),
    Transaction("t2", "a1", "food", -900, "2026-09-05", "x"),
    Transaction("t3", "a1", "food", -100, "2026-08-01", "x"),
)


def test_compose_applies_right_to_left():
    f = compose(lambda x: x + 1, lambda x: x * 2)
    assert f(3) == 7  # (3 * 2) + 1


def test_pipe_applies_left_to_right():
    result = pipe(3, lambda x: x * 2, lambda x: x + 1)
    assert result == 7  # (3 * 2) + 1


def test_compose_with_no_funcs_returns_input():
    f = compose()
    assert f(5) == 5


def test_budget_service_monthly_report_flags_exceeded():
    service = BudgetService(
        validators=[make_budget_validator(BUDGETS, TRANS)],
        calculators=[make_spending_calculator(TRANS)],
    )
    report = service.monthly_report("2026-09")
    assert report["spending"] == {"food": 1200}
    assert report["budgets_checked"] == ({"budget_id": "b1", "ok": False},)


def test_budget_service_report_has_steps_in_order():
    service = BudgetService(
        validators=[make_budget_validator(BUDGETS, TRANS)],
        calculators=[make_spending_calculator(TRANS)],
    )
    report = service.monthly_report("2026-08")
    assert report["steps"] == (
        "validated budgets for the month",
        "calculated spending per category",
    )


def test_budget_service_under_budget_month():
    service = BudgetService(
        validators=[make_budget_validator(BUDGETS, TRANS)],
        calculators=[make_spending_calculator(TRANS)],
    )
    report = service.monthly_report("2026-08")
    assert report["budgets_checked"] == ({"budget_id": "b1", "ok": True},)


def test_report_service_category_report():
    service = ReportService(aggregators=[make_category_aggregator(TRANS)])
    report = service.category_report("food")
    assert report["total"] == -1300
    assert report["count"] == 3
    assert report["steps"] == ("aggregated the category's transactions",)
