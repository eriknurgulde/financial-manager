"""Regenerate ``data/seed.json``.

Kept in the repository so the dataset is reproducible instead of being a magic
file nobody can explain: run it and you get byte-for-byte the same JSON, because
the RNG is seeded with a constant.

    python tools/generate_seed.py

Amounts are integers in tiins (1 KZT = 100 tiin). Income is positive, expense
is negative.
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 20_260_912
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "seed.json"

START = date(2026, 6, 1)
END = date(2026, 9, 12)

KZT = 100  # tiins per tenge


ACCOUNTS = [
    {
        "id": "a_kaspi",
        "name": "Kaspi Gold",
        "balance": 180_000 * KZT,
        "currency": "KZT",
    },
    {
        "id": "a_halyk",
        "name": "Halyk Debit",
        "balance": 95_000 * KZT,
        "currency": "KZT",
    },
    {"id": "a_cash", "name": "Cash", "balance": 25_000 * KZT, "currency": "KZT"},
]

# (id, name, parent_id, type)
CATEGORIES = [
    ("c_food", "Food", None, "expense"),
    ("c_food_groceries", "Groceries", "c_food", "expense"),
    ("c_food_cafe", "Cafes & Restaurants", "c_food", "expense"),
    ("c_food_coffee", "Coffee", "c_food", "expense"),
    ("c_transport", "Transport", None, "expense"),
    ("c_transport_taxi", "Taxi", "c_transport", "expense"),
    ("c_transport_fuel", "Fuel", "c_transport", "expense"),
    ("c_transport_public", "Public transport", "c_transport", "expense"),
    ("c_leisure", "Leisure", None, "expense"),
    ("c_leisure_cinema", "Cinema", "c_leisure", "expense"),
    ("c_leisure_games", "Games", "c_leisure", "expense"),
    ("c_leisure_travel", "Travel", "c_leisure", "expense"),
    ("c_home", "Home", None, "expense"),
    ("c_home_rent", "Rent", "c_home", "expense"),
    ("c_home_utilities", "Utilities", "c_home", "expense"),
    ("c_health", "Health", None, "expense"),
    ("c_health_pharmacy", "Pharmacy", "c_health", "expense"),
    ("c_income", "Income", None, "income"),
    ("c_income_salary", "Salary", "c_income", "income"),
    ("c_income_freelance", "Freelance", "c_income", "income"),
]

# leaf category -> (min KZT, max KZT, relative frequency, notes)
EXPENSE_PROFILE = {
    "c_food_groceries": (
        1_500,
        12_000,
        24,
        ["Small", "Magnum", "Galmart", "Corner shop"],
    ),
    "c_food_cafe": (2_000, 9_000, 14, ["Lunch", "Dinner with friends", "Burger place"]),
    "c_food_coffee": (600, 2_500, 18, ["Latte", "Americano", "Coffee to go"]),
    "c_transport_taxi": (700, 3_500, 16, ["Yandex Go", "InDrive", "Taxi home"]),
    "c_transport_fuel": (8_000, 25_000, 5, ["Helios", "KazMunayGas"]),
    "c_transport_public": (100, 600, 12, ["Bus", "Metro", "Onay top-up"]),
    "c_leisure_cinema": (2_000, 6_000, 4, ["Kinopark", "Chaplin cinema"]),
    "c_leisure_games": (3_000, 20_000, 4, ["Steam", "PS Store"]),
    "c_leisure_travel": (
        30_000,
        150_000,
        2,
        ["Bus to Almaty", "Hostel", "Train ticket"],
    ),
    "c_health_pharmacy": (1_000, 15_000, 5, ["Europharma", "Vitamins", "Painkillers"]),
}

BUDGETS = [
    {"id": "b_food", "cat_id": "c_food", "limit": 90_000 * KZT, "period": "month"},
    {
        "id": "b_transport",
        "cat_id": "c_transport",
        "limit": 45_000 * KZT,
        "period": "month",
    },
    {
        "id": "b_leisure",
        "cat_id": "c_leisure",
        "limit": 40_000 * KZT,
        "period": "month",
    },
    {
        "id": "b_coffee",
        "cat_id": "c_food_coffee",
        "limit": 6_000 * KZT,
        "period": "week",
    },
    {
        "id": "b_utilities",
        "cat_id": "c_home_utilities",
        "limit": 20_000 * KZT,
        "period": "month",
    },
]


def month_starts(start: date, end: date) -> list[date]:
    """Every first-of-month between `start` and `end`, inclusive."""
    out: list[date] = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        out.append(cursor)
        cursor = date(
            cursor.year + (cursor.month == 12),
            1 if cursor.month == 12 else cursor.month + 1,
            1,
        )
    return out


def stamp(rnd: random.Random, day: date) -> str:
    """An ISO timestamp at a plausible hour of the given day."""
    moment = datetime(day.year, day.month, day.day) + timedelta(
        hours=rnd.randint(7, 22), minutes=rnd.randrange(0, 60, 5)
    )
    return moment.isoformat(timespec="seconds")


def build_transactions(rnd: random.Random) -> list[dict]:
    rows: list[dict] = []

    def add(account_id: str, cat_id: str, amount: int, day: date, note: str) -> None:
        rows.append(
            {
                "id": f"t{len(rows) + 1:04d}",
                "account_id": account_id,
                "cat_id": cat_id,
                "amount": amount,
                "ts": stamp(rnd, day),
                "note": note,
            }
        )

    # Recurring monthly entries first: salary in, rent and utilities out.
    for first in month_starts(START, END):
        if first <= END:
            add(
                "a_kaspi",
                "c_income_salary",
                rnd.randint(350_000, 420_000) * KZT,
                first.replace(day=min(5, END.day if first.month == END.month else 5)),
                f"Salary {first:%B}",
            )
        rent_day = first.replace(day=3)
        if rent_day <= END:
            add("a_kaspi", "c_home_rent", -120_000 * KZT, rent_day, "Monthly rent")
        util_day = first.replace(day=10)
        if util_day <= END:
            add(
                "a_halyk",
                "c_home_utilities",
                -rnd.randint(9_000, 24_000) * KZT,
                util_day,
                "Utilities bill",
            )

    # Occasional freelance income.
    span = (END - START).days
    for _ in range(6):
        day = START + timedelta(days=rnd.randint(0, span))
        add(
            "a_halyk",
            "c_income_freelance",
            rnd.randint(30_000, 150_000) * KZT,
            day,
            "Freelance project",
        )

    # Everyday spending, weighted so groceries/coffee dominate the way they do
    # in a real statement.
    leaves = list(EXPENSE_PROFILE)
    weights = [EXPENSE_PROFILE[c][2] for c in leaves]
    for _ in range(110):
        cat_id = rnd.choices(leaves, weights=weights, k=1)[0]
        low, high, _freq, notes = EXPENSE_PROFILE[cat_id]
        day = START + timedelta(days=rnd.randint(0, span))
        account = rnd.choices(
            ["a_kaspi", "a_halyk", "a_cash"], weights=[60, 25, 15], k=1
        )[0]
        add(account, cat_id, -rnd.randint(low, high) * KZT, day, rnd.choice(notes))

    rows.sort(key=lambda r: r["ts"])
    # Renumber after sorting so ids run in chronological order.
    return [{**row, "id": f"t{i + 1:04d}"} for i, row in enumerate(rows)]


def main() -> None:
    rnd = random.Random(SEED)

    payload = {
        "accounts": ACCOUNTS,
        "categories": [
            {"id": cid, "name": name, "parent_id": parent, "type": ctype}
            for cid, name, parent, ctype in CATEGORIES
        ],
        "transactions": build_transactions(rnd),
        "budgets": BUDGETS,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"wrote {OUT_PATH}")
    print(f"  accounts     {len(payload['accounts'])}")
    print(f"  categories   {len(payload['categories'])}")
    print(f"  transactions {len(payload['transactions'])}")
    print(f"  budgets      {len(payload['budgets'])}")


if __name__ == "__main__":
    main()
