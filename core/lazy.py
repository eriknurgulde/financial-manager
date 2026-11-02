# Lazy evaluation for Lab 5.
# These functions use "yield" so nothing is computed until it is asked for.
# The full list of transactions/categories is built only at the final step
# (for example when Streamlit shows a dataframe, or a test calls list()).

from collections.abc import Callable, Iterable, Iterator

from core.domain import Category, Transaction


def iter_transactions(
    trans: tuple[Transaction, ...], pred: Callable[[Transaction], bool]
) -> Iterable[Transaction]:
    # Yield one transaction at a time if it passes pred.
    # Nothing is built in memory until someone iterates this.
    for t in trans:
        if pred(t):
            yield t


def lazy_top_categories(
    trans: Iterable[Transaction], cats: tuple[Category, ...], k: int
) -> Iterator[tuple[str, int]]:
    # Stream through trans once, add up expenses per category, then
    # yield only the top k categories. The running totals dict is the
    # only thing kept in memory while streaming.
    totals: dict[str, int] = {}
    for t in trans:
        if t.amount < 0:
            totals[t.cat_id] = totals.get(t.cat_id, 0) - t.amount

    names = {c.id: c.name for c in cats}
    ranked = sorted(totals.items(), key=lambda pair: pair[1], reverse=True)
    for cat_id, spent in ranked[:k]:
        yield names.get(cat_id, cat_id), spent
