# Async aggregations and final report for Lab 8.
# expenses_by_month and balance_forecast run one small coroutine per
# item (per month / per account) and asyncio.gather waits for all of
# them together, instead of one after another.

import asyncio

from core.domain import Account, Budget, Category, Transaction
from core.ftypes import check_budget
from core.lazy import iter_transactions, lazy_top_categories
from core.memo import forecast_expenses


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
    # One task per account: start balance plus all its transactions.
    async def forecast_for_account(acc: Account) -> tuple[str, int]:
        total = acc.balance + sum(t.amount for t in trans if t.account_id == acc.id)
        return acc.id, total

    results = await asyncio.gather(*(forecast_for_account(a) for a in accounts))
    return dict(results)


def build_final_report(
    accounts: tuple[Account, ...],
    categories: tuple[Category, ...],
    transactions: tuple[Transaction, ...],
    budgets: tuple[Budget, ...],
) -> dict:
    # End-to-end scenario: lazy filter -> lazy top categories -> cached
    # forecast per top category -> parallel monthly/account totals ->
    # one report dict with everything the UI needs.
    expenses = iter_transactions(transactions, lambda t: t.amount < 0)
    top_categories = tuple(lazy_top_categories(expenses, categories, 3))
    ids_by_name = {c.name: c.id for c in categories}
    forecasts = tuple(
        (name, forecast_expenses(ids_by_name[name], transactions, 1))
        for name, _spent in top_categories
    )

    months = sorted({t.ts[:7] for t in transactions})
    monthly = asyncio.run(expenses_by_month(list(transactions), months))
    balances = asyncio.run(balance_forecast(list(accounts), list(transactions)))
    exceeded = tuple(
        b.cat_id for b in budgets if not check_budget(b, transactions).is_right
    )

    return {
        "balances": balances,
        "top_categories": top_categories,
        "expenses_by_month": monthly,
        "exceeded_budgets": exceeded,
        "forecasts": forecasts,
    }
