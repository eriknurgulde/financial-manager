# Tests for Lab 8. Run them with: pytest -q

import asyncio

from core.async_ops import (
    balance_forecast,
    build_final_report,
    expenses_by_month,
    run_end_to_end,
)
from core.domain import Account, Budget, Category, Transaction
from core.report import budget_status, income_and_expenses, spending_by_category

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


def test_balance_forecast_is_balance_now_plus_average_monthly_change():
    # a1 changes by -400 in 2 months: balance now 9600, forecast 9600 - 200.
    result = asyncio.run(balance_forecast(list(ACCOUNTS), list(TRANS)))
    assert result == {"a1": 9400, "a2": 5750}


def test_balance_forecast_account_with_no_transactions():
    lone = (Account("a3", "Savings", 2000, "KZT"),)
    result = asyncio.run(balance_forecast(list(lone), list(TRANS)))
    assert result == {"a3": 2000}


def test_build_final_report_has_all_sections():
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS)
    assert set(report.keys()) == {
        "balances",
        "balance_forecast",
        "income",
        "expenses",
        "expenses_by_month",
        "month",
        "exceeded_budgets",
        "top_categories",
        "forecasts",
    }


def test_build_final_report_flags_exceeded_budget():
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS)
    assert report["month"] == "2026-09"
    assert report["exceeded_budgets"] == ("food",)


def test_build_final_report_budget_is_checked_for_the_last_month_only():
    # In August only 100 is spent and the limit is 100: not exceeded.
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS, end="2026-08-31")
    assert report["month"] == "2026-08"
    assert report["exceeded_budgets"] == ()


def test_build_final_report_filters_by_date_range():
    report = build_final_report(
        ACCOUNTS, CATS, TRANS, BUDGETS, start="2026-09-01", end="2026-09-30"
    )
    assert report["expenses_by_month"] == {"2026-09": 300}
    assert report["income"] == 500
    assert report["expenses"] == 300
    # the balances always use all transactions
    assert report["balances"] == {"a1": 9600, "a2": 5500}


def test_build_final_report_top_categories_and_forecasts_match():
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS)
    names_in_top = [name for name, _spent in report["top_categories"]]
    names_in_forecast = [name for name, _val in report["forecasts"]]
    assert names_in_top == names_in_forecast


def test_build_final_report_with_empty_period():
    report = build_final_report(ACCOUNTS, CATS, TRANS, BUDGETS, start="2030-01-01")
    assert report["expenses_by_month"] == {}
    assert report["exceeded_budgets"] == ()
    assert report["top_categories"] == ()


def test_run_end_to_end_loads_the_seed_file():
    report = run_end_to_end("data/seed.json")
    assert report["month"] == "2026-11"
    assert len(report["top_categories"]) == 3
    assert report["income"] > 0


def test_income_and_expenses():
    assert income_and_expenses(TRANS) == (500, 400)


def test_spending_by_category_names_and_sorting():
    cats = CATS + (Category("fun", "Fun", None, "expense"),)
    trans = TRANS + (Transaction("t4", "a1", "fun", -900, "2026-09-03", "x"),)
    assert spending_by_category(trans, cats) == {"Fun": 900, "Food": 400}


def test_budget_status_counts_only_the_given_month():
    september, august = (
        budget_status(BUDGETS, TRANS, m)[0] for m in ("2026-09", "2026-08")
    )
    assert (september["spent"], september["exceeded"]) == (300, True)
    assert (august["spent"], august["exceeded"]) == (100, False)
