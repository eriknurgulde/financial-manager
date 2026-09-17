# Memoized forecast function for Lab 3.
# lru_cache remembers past results, so calling the function again with the
# same arguments returns the saved answer instead of recomputing it.

import time
from functools import lru_cache

from core.domain import Transaction


@lru_cache
def forecast_expenses(cat_id: str, trans: tuple[Transaction, ...], period: int) -> int:
    # Forecast: average expense per period for one category.
    # trans is a tuple of frozen (hashable) Transactions, so the whole
    # argument list is immutable and works as a cache key.
    total = -sum(t.amount for t in trans if t.cat_id == cat_id and t.amount < 0)
    return total // period if period else 0


def measure_forecast(
    cat_id: str, trans: tuple[Transaction, ...], period: int
) -> tuple[int, float, float]:
    # Run forecast_expenses twice: first with an empty cache (slow path),
    # then again with the same arguments (fast, cached path).
    # Returns (result, time_before_ms, time_after_ms).
    forecast_expenses.cache_clear()

    start = time.perf_counter()
    result = forecast_expenses(cat_id, trans, period)
    before_ms = (time.perf_counter() - start) * 1000

    start = time.perf_counter()
    forecast_expenses(cat_id, trans, period)
    after_ms = (time.perf_counter() - start) * 1000

    return result, before_ms, after_ms
