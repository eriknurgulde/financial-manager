# Web API + site. Start it from the project folder:
#     uvicorn api.main:app --port 8600
# The API is a thin layer: every number comes from the pure functions in core/.

import asyncio
import itertools
import re
import subprocess
import sys
from dataclasses import asdict, is_dataclass, replace
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from core.async_ops import (
    balance_forecast,
    build_final_report,
    expenses_by_month,
)
from core.compose import compose, pipe
from core.domain import Transaction
from core.frp import (
    BALANCE_ALERT,
    BUDGET_ALERT,
    TRANSACTION_ADDED,
    EventBus,
    apply_transaction,
    check_balance_after_transaction,
    check_budget_after_transaction,
    on_balance_alert,
    on_budget_alert,
)
from core.ftypes import check_budget, safe_category, validate_transaction
from core.lazy import iter_transactions, lazy_top_categories
from core.memo import measure_forecast
from core.recursion import flatten_categories, sum_expenses_recursive
from core.report import (
    budget_status,
    income_and_expenses,
    spending_by_category,
)
from core.service import (
    BudgetService,
    ReportService,
    make_budget_validator,
    make_category_aggregator,
    make_spending_calculator,
)
from core.transforms import (
    account_balance,
    add_transaction,
    by_amount_range,
    by_category,
    by_date_range,
    load_seed,
    total_balance,
    update_budget,
)

accounts, categories, transactions, budgets = load_seed(ROOT / "data" / "seed.json")
LAST_DATE = max(t.ts for t in transactions)
FIRST_DATE = min(t.ts for t in transactions)
MONTHS = sorted({t.ts[:7] for t in transactions})
LEAF_IDS = [c.id for c in categories if all(x.parent_id != c.id for x in categories)]
ROOT_IDS = [c.id for c in categories if c.parent_id is None]
NAMES = {c.id: c.name for c in categories}

app = FastAPI(title="Financial Manager API")


def jsonable(value):
    # Dataclasses, tuples and dicts to plain JSON types.
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def check_cat(cat_id: str) -> str:
    if cat_id not in NAMES:
        raise HTTPException(404, f"category not found: {cat_id}")
    return cat_id


# ------------------------------------------------------------------ data ---
@app.get("/api/meta")
def meta():
    return {
        "first_date": FIRST_DATE,
        "last_date": LAST_DATE,
        "months": MONTHS,
        "leaf_ids": LEAF_IDS,
        "root_ids": ROOT_IDS,
        "names": NAMES,
        "accounts": jsonable(accounts),
        "transaction_ids": [t.id for t in transactions],
    }


@app.get("/api/overview")
def overview():
    income, spent = income_and_expenses(transactions)
    monthly = asyncio.run(expenses_by_month(list(transactions), MONTHS))
    income_by_month = {
        m: sum(t.amount for t in transactions if t.ts.startswith(m) and t.amount > 0)
        for m in MONTHS
    }
    return {
        "counts": {
            "accounts": len(accounts),
            "categories": len(categories),
            "transactions": len(transactions),
        },
        "total_balance": total_balance(accounts, transactions),
        "income": income,
        "expenses": spent,
        "saved": income - spent,
        "by_month": [
            {"month": m, "income": income_by_month[m], "expenses": monthly[m]}
            for m in MONTHS
        ],
        "accounts": [
            {**asdict(a), "current": a.balance + account_balance(transactions, a.id)}
            for a in accounts
        ],
        "by_category": spending_by_category(transactions, categories),
    }


@app.get("/api/data")
def data():
    return {
        "accounts": jsonable(accounts),
        "categories": jsonable(categories),
        "budgets": jsonable(budgets),
        "transactions": jsonable(
            sorted(transactions, key=lambda t: t.ts, reverse=True)
        ),
    }


# --------------------------------------------------------- functional core --
@app.get("/api/core/balances")
def core_balances():
    return [
        {"name": a.name, "balance": account_balance(transactions, a.id)}
        for a in accounts
    ]


@app.get("/api/core/immutability")
def core_immutability(limit: int | None = None):
    new_t = Transaction("t_new", "acc1", "cafe", -5000, LAST_DATE, "Demo")
    new_list = add_transaction(transactions, new_t)
    first = budgets[0]
    new_limit = first.limit + 10000 if limit is None else limit
    new_budgets = update_budget(budgets, first.id, new_limit)
    return {
        "old_count": len(transactions),
        "new_count": len(new_list),
        "budget_id": first.id,
        "budget_cat": first.cat_id,
        "old_limit": first.limit,
        "new_limit": new_budgets[0].limit,
    }


@app.get("/api/core/filter")
def core_filter(
    cat: str,
    min_amount: int = -10_000_000,
    max_amount: int = 10_000_000,
    start: str = "0000-01-01",
    end: str = "9999-12-31",
):
    cat_filter = by_category(cat)
    amount_filter = by_amount_range(min_amount, max_amount)
    date_filter = by_date_range(start, end)
    found = [
        t for t in transactions if cat_filter(t) and amount_filter(t) and date_filter(t)
    ]
    return {"count": len(found), "transactions": jsonable(found)}


@app.get("/api/core/maybe")
def core_maybe(cat_id: str):
    name = safe_category(categories, cat_id).map(lambda c: c.name).get_or_else(None)
    return {"cat_id": cat_id, "found": name is not None, "name": name}


@app.get("/api/core/compose")
def core_compose(x: int):
    to_positive = abs

    def double(n):
        return n * 2

    return {
        "x": x,
        "compose": compose(double, to_positive)(x),
        "pipe": pipe(x, to_positive, double),
    }


# --------------------------------------------------------------- pipelines --
@app.get("/api/pipelines/hierarchy")
def pipelines_hierarchy(root: str):
    check_cat(root)
    tree = flatten_categories(categories, root)
    return {
        "root": root,
        "tree": [{"id": c.id, "name": c.name, "parent_id": c.parent_id} for c in tree],
        "total": sum_expenses_recursive(categories, transactions, root),
        "by_category": {
            c.name: sum_expenses_recursive(categories, transactions, c.id) for c in tree
        },
    }


@app.get("/api/pipelines/stream")
def pipelines_stream(max_amount: int = -5000, repeat: int = 100):
    repeat = max(1, min(repeat, 5000))
    big_stream = itertools.chain.from_iterable(itertools.repeat(transactions, repeat))
    matching = iter_transactions(big_stream, lambda t: t.amount <= max_amount)
    return {
        "stream_size": len(transactions) * repeat,
        "matching": sum(1 for _ in matching),
    }


# ----------------------------------------------------------------- reports --
@app.get("/api/reports/forecast")
def reports_forecast(cat: str, period: int = 1):
    check_cat(cat)
    result, before_ms, after_ms = measure_forecast(cat, transactions, max(1, period))
    return {"value": result, "before_ms": before_ms, "after_ms": after_ms}


@app.get("/api/reports/validate")
def reports_validate(t_id: str):
    picked = next((t for t in transactions if t.id == t_id), None)
    if picked is None:
        raise HTTPException(404, "transaction not found")
    result = validate_transaction(picked, accounts, categories)
    budget = next((b for b in budgets if b.cat_id == picked.cat_id), None)
    if result.is_right and budget is not None:
        same_month = tuple(t for t in transactions if t.ts[:7] == picked.ts[:7])
        result = check_budget(budget, same_month).map(lambda _b: picked)
    return {
        "id": t_id,
        "transaction": jsonable(picked),
        "valid": result.is_right,
        "error": None if result.is_right else result.left,
    }


@app.get("/api/reports/top")
def reports_top(k: int = 3):
    expenses = iter_transactions(transactions, lambda t: t.amount < 0)
    top = list(lazy_top_categories(expenses, categories, max(1, k)))
    return [{"name": name, "spent": spent} for name, spent in top]


@app.get("/api/reports/budget")
def reports_budget(month: str):
    service = BudgetService(
        validators=[make_budget_validator(budgets, transactions)],
        calculators=[make_spending_calculator(transactions)],
    )
    report = service.monthly_report(month)
    return {
        "month": month,
        "steps": jsonable(report["steps"]),
        "spending": report["spending"],
        "budgets_checked": jsonable(report["budgets_checked"]),
        "status": jsonable(budget_status(budgets, transactions, month)),
    }


@app.get("/api/reports/category")
def reports_category(cat: str):
    check_cat(cat)
    service = ReportService(aggregators=[make_category_aggregator(transactions)])
    report = service.category_report(cat)
    return jsonable(report)


@app.get("/api/reports/final")
def reports_final(start: str = FIRST_DATE, end: str = LAST_DATE):
    return jsonable(
        build_final_report(accounts, categories, transactions, budgets, start, end)
    )


# --------------------------------------------------------------- async/frp --
def make_bus() -> EventBus:
    current = tuple(
        replace(a, balance=a.balance + account_balance(transactions, a.id))
        for a in accounts
    )
    bus = EventBus(
        {
            "accounts": current,
            "budgets": budgets,
            "transactions": transactions,
            "notifications": (),
        }
    )
    bus.subscribe(TRANSACTION_ADDED, apply_transaction)
    bus.subscribe(TRANSACTION_ADDED, check_budget_after_transaction)
    bus.subscribe(TRANSACTION_ADDED, check_balance_after_transaction)
    bus.subscribe(BUDGET_ALERT, on_budget_alert)
    bus.subscribe(BALANCE_ALERT, on_balance_alert)
    return bus


bus = make_bus()


def bus_state() -> dict:
    return {
        "accounts": jsonable(bus.state["accounts"]),
        "notifications": list(bus.state["notifications"]),
        "transactions": len(bus.state["transactions"]),
    }


class Publish(BaseModel):
    name: str
    account_id: str = "acc1"
    cat_id: str = "cafe"
    amount: int = -5000


@app.get("/api/frp/state")
def frp_state():
    return bus_state()


@app.post("/api/frp/publish")
def frp_publish(body: Publish):
    if body.name == TRANSACTION_ADDED:
        check_cat(body.cat_id)
        if body.account_id not in {a.id for a in accounts}:
            raise HTTPException(404, "account not found")
        new_t = Transaction(
            f"t_evt_{len(bus.state['transactions'])}",
            body.account_id,
            body.cat_id,
            body.amount,
            LAST_DATE,
            "FRP demo",
        )
        bus.publish(TRANSACTION_ADDED, {"transaction": new_t})
    elif body.name == BUDGET_ALERT:
        bus.publish(BUDGET_ALERT, {"message": f"Manual budget alert for {body.cat_id}"})
    elif body.name == BALANCE_ALERT:
        bus.publish(
            BALANCE_ALERT, {"message": f"Low balance warning for {body.account_id}"}
        )
    else:
        raise HTTPException(400, "unknown event name")
    return bus_state()


@app.post("/api/frp/reset")
def frp_reset():
    global bus
    bus = make_bus()
    return bus_state()


@app.get("/api/async")
def async_aggregations():
    monthly = asyncio.run(expenses_by_month(list(transactions), MONTHS))
    forecast = asyncio.run(balance_forecast(list(accounts), list(transactions)))
    return {"expenses_by_month": monthly, "balance_forecast": forecast}


# ------------------------------------------------------------- tests/about --
@app.get("/api/tests")
def tests_info():
    counts = {
        f.name: len(
            re.findall(r"^def test_", f.read_text(encoding="utf-8"), re.MULTILINE)
        )
        for f in sorted((ROOT / "tests").glob("test_lab*.py"))
    }
    return {"counts": counts, "total": sum(counts.values())}


@app.post("/api/tests/run")
def tests_run():
    # Fixed command, nothing from the browser goes into it. A subprocess keeps
    # the tests away from the running server and its event bus.
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-v",
                "--tb=short",
                "-p",
                "no:cacheprovider",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "tests took longer than 60 seconds")
    files: dict[str, list[dict]] = {}
    for m in re.finditer(
        r"^tests/(\S+?)::(\S+) (PASSED|FAILED|ERROR)", proc.stdout, re.MULTILINE
    ):
        files.setdefault(m[1], []).append({"name": m[2], "status": m[3]})
    summary = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    failed = proc.returncode != 0
    return {
        "ok": not failed,
        "summary": summary.strip("= "),
        "files": files,
        "log": proc.stdout[-4000:] if failed else "",
    }


# ------------------------------------------------------------------- site ---
WEB = ROOT / "web"


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
