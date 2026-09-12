"""The I/O boundary of the application.

Reading a file is a side effect, so it lives here and nowhere else. It is kept
as thin as possible - `read_seed_text` touches the disk, `parse_seed` is pure -
so that everything interesting can be tested without a filesystem:

    parse_seed(json.loads(text))   # pure, no disk
    load_seed("data/seed.json")    # the impure convenience wrapper

`core.transforms` stays 100% pure and never imports this module.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.domain import Account, Budget, Category, Transaction

SeedData = tuple[
    tuple[Account, ...],
    tuple[Category, ...],
    tuple[Transaction, ...],
    tuple[Budget, ...],
]

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seed.json"


class SeedFormatError(ValueError):
    """Raised when the seed file is structurally wrong (missing keys, bad types)."""


def _require(payload: dict, key: str) -> list:
    """Pull a list out of the payload or explain precisely what is missing."""
    if key not in payload:
        raise SeedFormatError(f"seed is missing the {key!r} section")
    value = payload[key]
    if not isinstance(value, list):
        raise SeedFormatError(f"{key!r} must be a list, got {type(value).__name__}")
    return value


def parse_seed(payload: dict) -> SeedData:
    """Turn a decoded JSON payload into immutable domain tuples.

    Pure: same input, same output, no side effects. Unknown keys in each record
    are rejected loudly rather than silently ignored, because a typo in the seed
    file should not quietly produce an entity with a default value.
    """
    if not isinstance(payload, dict):
        raise SeedFormatError(
            f"seed must be a JSON object, got {type(payload).__name__}"
        )

    try:
        accounts = tuple(Account(**row) for row in _require(payload, "accounts"))
        categories = tuple(Category(**row) for row in _require(payload, "categories"))
        transactions = tuple(
            Transaction(**row) for row in _require(payload, "transactions")
        )
        budgets = tuple(Budget(**row) for row in _require(payload, "budgets"))
    except TypeError as exc:  # wrong/missing field on one of the records
        raise SeedFormatError(f"malformed record in seed: {exc}") from exc

    return accounts, categories, transactions, budgets


def read_seed_text(path: str | Path) -> str:
    """The only function in `core` that touches the disk."""
    return Path(path).read_text(encoding="utf-8")


def load_seed(path: str | Path = DEFAULT_SEED_PATH) -> SeedData:
    """Read the seed file and decode it into immutable tuples."""
    return parse_seed(json.loads(read_seed_text(path)))


__all__ = [
    "DEFAULT_SEED_PATH",
    "SeedData",
    "SeedFormatError",
    "load_seed",
    "parse_seed",
    "read_seed_text",
]
