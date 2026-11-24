# Async aggregations and final report for Lab 8.
# expenses_by_month and balance_forecast run one small coroutine per
# item (per month / per account) and asyncio.gather waits for all of
# them together, instead of one after another.

import asyncio

from core.domain import Account, Budget, Category, Transaction
from core.lazy import iter_transactions, lazy_top_categories
from core.memo import forecast_expenses
from core.report import budget_status, income_and_expenses
from core.transforms import account_balance, by_date_range, load_seed


async def expenses_by_month(
    trans: list[Transaction], months: list[str]
) -> dict[str, int]:
    # One task per month: total expenses that started in that month.
    async def total_for_month(month: str) -> tuple[str, int]:
        spent = -sum(t.amount for t in trans if t.ts.startswith(month) and t.amount < 0)
        return month, spent

    results = await asyncio.gather(*(total_for_month(m) for m in months))
    return dict(results)


async def balance_forecast(
    accounts: list[Account], trans: list[Transaction]
) -> dict[str, int]:
    # One task per account. Forecast = balance now + the average monthly
    # change of this account (what it gained or lost per month so far).
    months = len({t.ts[:7] for t in trans}) or 1

    async def forecast_for_account(acc: Account) -> tuple[str, int]:
        change = sum(t.amount for t in trans if t.account_id == acc.id)
        return acc.id, acc.balance + change + round(change / months)

    results = await asyncio.gather(*(forecast_for_account(a) for a in accounts))
    return dict(results)


def build_final_report(
    accounts: tuple[Account, ...],
    categories: tuple[Category, ...],
    transactions: tuple[Transaction, ...],
    budgets: tuple[Budget, ...],
    start: str = "0000-01-01",
    end: str = "9999-12-31",
) -> dict:
    # End-to-end scenario, one step after another:
    # 1) filter: only transactions from start to end (closure + generator)
    # 2) lazy generators: stream the expenses into the top categories
    # 3) cached forecast: average monthly spending of each top category
    # 4) parallel totals: expenses per month and balance forecast per account
    # 5) one report dict with balance, expenses and exceeded budgets
    chosen = tuple(iter_transactions(transactions, by_date_range(start, end)))
    months = sorted({t.ts[:7] for t in chosen})

    expenses = iter_transactions(chosen, lambda t: t.amount < 0)
    top_categories = tuple(lazy_top_categories(expenses, categories, 3))
    ids_by_name = {c.name: c.id for c in categories}
    forecasts = tuple(
        (name, forecast_expenses(ids_by_name[name], chosen, len(months) or 1))
        for name, _spent in top_categories
    )

    monthly = asyncio.run(expenses_by_month(list(chosen), months))
    forecast = asyncio.run(balance_forecast(list(accounts), list(transactions)))
    balances = {a.id: a.balance + account_balance(transactions, a.id) for a in accounts}

    # Budgets are monthly, so check the last month of the chosen period.
    last_month = months[-1] if months else ""
    exceeded = tuple(
        row["cat_id"]
        for row in budget_status(budgets, chosen, last_month)
        if months and row["exceeded"]
    )
    income, spent = income_and_expenses(chosen)

    return {
        "balances": balances,
        "balance_forecast": forecast,
        "income": income,
        "expenses": spent,
        "expenses_by_month": monthly,
        "month": last_month,
        "exceeded_budgets": exceeded,
        "top_categories": top_categories,
        "forecasts": forecasts,
    }


def run_end_to_end(path: str, start: str = "0000-01-01", end: str = "9999-12-31"):
    # The whole scenario from a file: load -> filter -> ... -> final report.
    accounts, categories, transactions, budgets = load_seed(path)
    return build_final_report(accounts, categories, transactions, budgets, start, end)
