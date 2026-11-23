# Pure report helpers (budget, spending and category reports).
# They only read their inputs and return new tuples/dicts, nothing else.

from core.domain import Budget, Category, Transaction
from core.ftypes import check_budget


def income_and_expenses(trans: tuple[Transaction, ...]) -> tuple[int, int]:
    # Returns (income, expenses). Expenses are returned as a positive number.
    income = sum(t.amount for t in trans if t.amount > 0)
    expenses = -sum(t.amount for t in trans if t.amount < 0)
    return income, expenses


def spending_by_category(
    trans: tuple[Transaction, ...], cats: tuple[Category, ...]
) -> dict[str, int]:
    # Total expenses per category name, biggest first.
    names = {c.id: c.name for c in cats}
    totals: dict[str, int] = {}
    for t in trans:
        if t.amount < 0:
            name = names.get(t.cat_id, t.cat_id)
            totals[name] = totals.get(name, 0) - t.amount
    return dict(sorted(totals.items(), key=lambda pair: pair[1], reverse=True))


def budget_status(
    budgets: tuple[Budget, ...], trans: tuple[Transaction, ...], month: str
) -> tuple[dict, ...]:
    # A budget limit is for one month, so only that month's transactions
    # count. Each row: budget id, category, limit, spent and a flag.
    month_trans = tuple(t for t in trans if t.ts.startswith(month))
    rows = []
    for b in budgets:
        spent = -sum(
            t.amount for t in month_trans if t.cat_id == b.cat_id and t.amount < 0
        )
        rows.append(
            {
                "budget_id": b.id,
                "cat_id": b.cat_id,
                "limit": b.limit,
                "spent": spent,
                "exceeded": not check_budget(b, month_trans).is_right,
            }
        )
    return tuple(rows)
