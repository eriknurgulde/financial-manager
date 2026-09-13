"""Pure transformations over the domain tuples.

Every function here is pure: it reads its arguments, returns a new value, and
touches nothing else. No I/O, no globals, no mutation of the inputs - the
"update" functions build a new tuple rather than editing the one they were
given.

The four functions required by Lab 1 are :func:`load_seed` (in
:mod:`core.loader`, because it does I/O), :func:`add_transaction`,
:func:`update_budget` and :func:`account_balance`. The rest are the small
building blocks the Overview screen is assembled from.

Balance model
-------------
``Account.balance`` is the **opening** balance - what was on the account before
the transaction log starts. :func:`account_balance` sums only the transactions,
which is what the assignment signature allows for. The number a user actually
cares about is the two added together, which is :func:`current_balance`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from functools import reduce
from operator import add

from core.domain import Account, Budget, Category, Transaction

# --------------------------------------------------------------------------
# Required by the Lab 1 specification
# --------------------------------------------------------------------------


def add_transaction(
    trans: tuple[Transaction, ...], t: Transaction
) -> tuple[Transaction, ...]:
    """Return a new tuple with `t` appended. `trans` is left untouched."""
    return (*trans, t)


def update_budget(
    budgets: tuple[Budget, ...], bid: str, new_limit: int
) -> tuple[Budget, ...]:
    """Return a new tuple where budget `bid` has `new_limit`.

    Budgets are frozen, so the matching one is replaced by a fresh value rather
    than edited. An unknown `bid` is not an error: the result is simply an
    equal tuple. That keeps the function total - the UI never has to guard the
    call - and :func:`find_budget` is available when the caller does want to
    know whether the budget exists.
    """
    return tuple(
        map(
            lambda b: replace(b, limit=new_limit) if b.id == bid else b,
            budgets,
        )
    )


def account_balance(trans: tuple[Transaction, ...], acc_id: str) -> int:
    """Net movement on one account: income minus expenses, via `reduce`.

    No branching on the sign is needed because expenses are already stored as
    negative numbers, so the fold is a plain sum.
    """
    return reduce(
        add,
        map(
            lambda t: t.amount,
            filter(lambda t: t.account_id == acc_id, trans),
        ),
        0,
    )


# --------------------------------------------------------------------------
# Building blocks for the Overview screen
# --------------------------------------------------------------------------


def current_balance(account: Account, trans: tuple[Transaction, ...]) -> int:
    """Opening balance plus everything that has moved since."""
    return account.balance + account_balance(trans, account.id)


def total_balance(accounts: tuple[Account, ...], trans: tuple[Transaction, ...]) -> int:
    """Money across all accounts."""
    return reduce(add, map(lambda a: current_balance(a, trans), accounts), 0)


def total_income(trans: tuple[Transaction, ...]) -> int:
    """Sum of the positive amounts."""
    return reduce(add, map(lambda t: t.amount, filter(is_income, trans)), 0)


def total_expenses(trans: tuple[Transaction, ...]) -> int:
    """Sum of the expenses, as a positive magnitude."""
    return -reduce(add, map(lambda t: t.amount, filter(is_expense, trans)), 0)


def is_income(t: Transaction) -> bool:
    return t.amount > 0


def is_expense(t: Transaction) -> bool:
    return t.amount < 0


def find_account(accounts: tuple[Account, ...], acc_id: str) -> Account | None:
    """First account with that id, or None. Lab 4 replaces this with Maybe."""
    return next(filter(lambda a: a.id == acc_id, accounts), None)


def find_category(cats: tuple[Category, ...], cat_id: str) -> Category | None:
    return next(filter(lambda c: c.id == cat_id, cats), None)


def find_budget(budgets: tuple[Budget, ...], bid: str) -> Budget | None:
    return next(filter(lambda b: b.id == bid, budgets), None)


def where(
    trans: tuple[Transaction, ...], predicate: Callable[[Transaction], bool]
) -> tuple[Transaction, ...]:
    """Filter transactions with any predicate - the HOF the Lab 2 closures plug into."""
    return tuple(filter(predicate, trans))


def sum_amounts(trans: Iterable[Transaction]) -> int:
    """Fold any iterable of transactions down to one number."""
    return reduce(add, map(lambda t: t.amount, trans), 0)


def expenses_by_category(trans: tuple[Transaction, ...]) -> dict[str, int]:
    """Expense magnitude per category id, for the categories that have any.

    Only direct hits - rolling child categories up into their parent needs the
    recursive walk from Lab 2.
    """
    return reduce(
        lambda acc, t: {**acc, t.cat_id: acc.get(t.cat_id, 0) + -t.amount},
        filter(is_expense, trans),
        {},
    )


def overview(
    accounts: tuple[Account, ...],
    cats: tuple[Category, ...],
    trans: tuple[Transaction, ...],
) -> dict[str, int]:
    """The four headline numbers the Overview menu item has to show."""
    return {
        "accounts": len(accounts),
        "categories": len(cats),
        "transactions": len(trans),
        "total_balance": total_balance(accounts, trans),
        "total_income": total_income(trans),
        "total_expenses": total_expenses(trans),
    }


def format_money(amount: int, currency: str = "KZT") -> str:
    """Render minor units as a human amount: ``-450000 -> '-4 500.00 KZT'``."""
    sign = "-" if amount < 0 else ""
    whole, minor = divmod(abs(amount), 100)
    return f"{sign}{whole:,}".replace(",", " ") + f".{minor:02d} {currency}"


__all__ = [
    "account_balance",
    "add_transaction",
    "current_balance",
    "expenses_by_category",
    "find_account",
    "find_budget",
    "find_category",
    "format_money",
    "is_expense",
    "is_income",
    "overview",
    "sum_amounts",
    "total_balance",
    "total_expenses",
    "total_income",
    "update_budget",
    "where",
]
