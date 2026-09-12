"""Tests for the seed loader and for the shape of the shipped dataset."""

import json

import pytest

from core.domain import Account, Budget, Category
from core.loader import (
    DEFAULT_SEED_PATH,
    SeedFormatError,
    load_seed,
    parse_seed,
)

MINIMAL = {
    "accounts": [{"id": "a1", "name": "Cash", "balance": 100, "currency": "KZT"}],
    "categories": [{"id": "c1", "name": "Food", "parent_id": None, "type": "expense"}],
    "transactions": [
        {
            "id": "t1",
            "account_id": "a1",
            "cat_id": "c1",
            "amount": -50,
            "ts": "2026-09-01T10:00:00",
            "note": "lunch",
        }
    ],
    "budgets": [{"id": "b1", "cat_id": "c1", "limit": 500, "period": "month"}],
}


def test_parse_seed_returns_tuples_of_domain_objects():
    accounts, categories, transactions, budgets = parse_seed(MINIMAL)

    assert isinstance(accounts, tuple)
    assert isinstance(categories, tuple)
    assert isinstance(transactions, tuple)
    assert isinstance(budgets, tuple)
    assert accounts == (Account(id="a1", name="Cash", balance=100, currency="KZT"),)
    assert categories[0] == Category(
        id="c1", name="Food", parent_id=None, type="expense"
    )
    assert transactions[0].amount == -50
    assert budgets[0] == Budget(id="b1", cat_id="c1", limit=500, period="month")


def test_parse_seed_is_pure_and_does_not_touch_its_input():
    payload = json.loads(json.dumps(MINIMAL))
    before = json.dumps(payload, sort_keys=True)

    parse_seed(payload)

    assert json.dumps(payload, sort_keys=True) == before


def test_parse_seed_is_deterministic():
    assert parse_seed(MINIMAL) == parse_seed(MINIMAL)


@pytest.mark.parametrize(
    "missing", ["accounts", "categories", "transactions", "budgets"]
)
def test_missing_section_is_reported_by_name(missing):
    payload = {k: v for k, v in MINIMAL.items() if k != missing}

    with pytest.raises(SeedFormatError, match=missing):
        parse_seed(payload)


def test_section_of_the_wrong_type_is_rejected():
    payload = {**MINIMAL, "accounts": {"id": "a1"}}

    with pytest.raises(SeedFormatError, match="must be a list"):
        parse_seed(payload)


def test_record_with_an_unknown_field_is_rejected_loudly():
    payload = {
        **MINIMAL,
        "accounts": [
            {"id": "a1", "name": "Cash", "balance": 1, "currency": "KZT", "typo": 1}
        ],
    }

    with pytest.raises(SeedFormatError, match="malformed record"):
        parse_seed(payload)


def test_non_object_payload_is_rejected():
    with pytest.raises(SeedFormatError, match="must be a JSON object"):
        parse_seed([1, 2, 3])


def test_shipped_seed_meets_the_assignment_minimums():
    accounts, categories, transactions, budgets = load_seed(DEFAULT_SEED_PATH)

    assert len(accounts) >= 3
    assert len(categories) >= 10
    assert len(transactions) >= 100
    assert len(budgets) >= 3


def test_shipped_seed_has_the_required_category_hierarchy():
    _, categories, _, _ = load_seed(DEFAULT_SEED_PATH)
    by_id = {c.id: c for c in categories}

    for root in ("c_food", "c_transport", "c_leisure"):
        assert by_id[root].parent_id is None
        children = [c for c in categories if c.parent_id == root]
        assert children, f"{root} must have at least one child category"


def test_shipped_seed_is_referentially_consistent():
    accounts, categories, transactions, budgets = load_seed(DEFAULT_SEED_PATH)
    account_ids = {a.id for a in accounts}
    category_ids = {c.id for c in categories}

    assert all(t.account_id in account_ids for t in transactions)
    assert all(t.cat_id in category_ids for t in transactions)
    assert all(b.cat_id in category_ids for b in budgets)
    assert all(c.parent_id is None or c.parent_id in category_ids for c in categories)


def test_shipped_seed_ids_are_unique():
    accounts, categories, transactions, budgets = load_seed(DEFAULT_SEED_PATH)

    for group in (accounts, categories, transactions, budgets):
        ids = [item.id for item in group]
        assert len(ids) == len(set(ids))


def test_shipped_seed_is_stored_with_lf_line_endings():
    """Guards the reproducibility claim in the README.

    `.gitattributes` normalises the repository to LF, so a checkout on any OS
    has LF. If the generator wrote CRLF (which Python does by default on
    Windows), regenerating the file would produce different bytes than the ones
    git stores and "run it twice, get the same file" would quietly stop being
    true for half the team.
    """
    raw = DEFAULT_SEED_PATH.read_bytes()

    assert b"\r\n" not in raw


def test_shipped_seed_respects_the_sign_convention():
    _, categories, transactions, _ = load_seed(DEFAULT_SEED_PATH)
    kind = {c.id: c.type for c in categories}

    for t in transactions:
        if kind[t.cat_id] == "income":
            assert t.amount > 0, f"{t.id} is income but not positive"
        else:
            assert t.amount < 0, f"{t.id} is an expense but not negative"
