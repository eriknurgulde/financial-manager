# Tests for Lab 8. Run them with: pytest -q

import asyncio

from core.async_ops import balance_forecast, build_final_report, expenses_by_month
from core.domain import Account, Budget, Category, Transaction

ACCOUNTS = (
    Account("a1", "Wallet", 10000, "KZT"),
    Account("a2", "Card", 5000, "KZT"),
)
CATS = (Category("food", "Food", None, "expense"),)
BUDGETS = (Budget("b1", "food", 100, "month"),)
TRANS = (
    Transaction("t1", "a1", "food", -300, "2026-09-01", "x"),
    Transaction("t2", "a1", "food", -100, "2026-08-01", "x"),
    Transaction("t3", "a2", "food", 500, "2026-09-02", "income"),
)


def test_expenses_by_month_totals_each_month():
    result = asyncio.run(expenses_by_month(list(TRANS), ["2026-09", "2026-08"]))
    assert result == {"2026-09": 300, "2026-08": 100}


def test_expenses_by_month_empty_month_is_zero():
    result = asyncio.run(expenses_by_month(list(TRANS), ["2026-01"]))
    assert result == {"2026-01": 0}


def test_balance_forecast_adds_transactions_to_start_balance():
    result = asyncio.run(balance_forecast(list(ACCOUNTS), list(TRANS)))
    assert result == {"a1": 9600, "a2": 5500}


def test_balance_forecast_account_with_no_transactions():
    lone = (Account("a3", "Savings", 2000, "KZT"),)
    result = asyncio.run(balance_forecast(list(lone), list(TRANS)))
    assert result == {"a3": 2000}


def test_build_final_report_has_all_sections():
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS)
    assert set(report.keys()) == {
        "balances",
        "top_categories",
        "expenses_by_month",
        "exceeded_budgets",
        "forecasts",
    }


def test_build_final_report_flags_exceeded_budget():
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS)
    assert report["exceeded_budgets"] == ("food",)


def test_build_final_report_top_categories_and_forecasts_match():
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS)
    names_in_top = [name for name, _spent in report["top_categories"]]
    names_in_forecast = [name for name, _val in report["forecasts"]]
    assert names_in_top == names_in_forecast
