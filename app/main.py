# Streamlit web app. Start it from the project folder:
#     streamlit run app/main.py

import itertools
import sys
from dataclasses import asdict
from pathlib import Path

import streamlit as st

# Streamlit starts from the app/ folder, so Python can not see core/.
# We add the project folder to the import path to fix this.
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from core.compose import compose, pipe
from core.domain import Transaction
from core.frp import (
    BALANCE_ALERT,
    BUDGET_ALERT,
    TRANSACTION_ADDED,
    EventBus,
    apply_transaction,
    check_budget_after_transaction,
    on_balance_alert,
    on_budget_alert,
)
from core.ftypes import check_budget, safe_category, validate_transaction
from core.lazy import iter_transactions, lazy_top_categories
from core.memo import measure_forecast
from core.recursion import flatten_categories, sum_expenses_recursive
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
    load_seed,
    total_balance,
    update_budget,
)

MENU = [
    "Overview",
    "Data",
    "Functional Core",
    "Pipelines",
    "Async/FRP",
    "Reports",
    "Tests",
    "About",
]

st.set_page_config(page_title="Financial Manager", layout="wide")

# Load the data from the JSON file.
accounts, categories, transactions, budgets = load_seed(ROOT / "data" / "seed.json")

# The sidebar is our burger menu (on a phone it hides behind the ☰ button).
page = st.sidebar.radio("Menu", MENU)

if page == "Overview":
    # Lab 1 task: show counts and the total balance.
    st.title("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accounts", len(accounts))
    col2.metric("Categories", len(categories))
    col3.metric("Transactions", len(transactions))
    col4.metric("Total balance", f"{total_balance(accounts, transactions)} KZT")

elif page == "Data":
    # Show the loaded data as tables.
    st.title("Data")
    st.subheader("Accounts")
    st.dataframe([asdict(a) for a in accounts])
    st.subheader("Categories")
    st.dataframe([asdict(c) for c in categories])
    st.subheader("Budgets")
    st.dataframe([asdict(b) for b in budgets])
    st.subheader("Transactions")
    st.dataframe([asdict(t) for t in transactions])

elif page == "Functional Core":
    # Small demo of the Lab 1 functions.
    st.title("Functional Core")

    st.subheader("account_balance")
    for a in accounts:
        st.write(f"{a.name}: {account_balance(transactions, a.id)} KZT")

    st.subheader("add_transaction")
    new_t = Transaction("t_new", "acc1", "cafe", -5000, "2026-09-12", "Demo")
    new_list = add_transaction(transactions, new_t)
    # The old tuple did not change, we got a new one with one more item.
    st.write(f"Old tuple: {len(transactions)} items")
    st.write(f"New tuple: {len(new_list)} items")

    st.subheader("update_budget")
    new_limit = st.number_input("New limit for b1 (Food)", value=120000, step=1000)
    new_budgets = update_budget(budgets, "b1", int(new_limit))
    st.write(f"Old limit: {budgets[0].limit} KZT")
    st.write(f"New limit: {new_budgets[0].limit} KZT")

    # Lab 2 task: closures demo (by_category, by_amount_range).
    st.subheader("Closures: filters")
    cat_id = st.selectbox("Category", [c.id for c in categories])
    min_a, max_a = st.slider("Amount range", -50000, 50000, (-50000, 50000))
    cat_filter = by_category(cat_id)
    amount_filter = by_amount_range(min_a, max_a)
    found = [t for t in transactions if cat_filter(t) and amount_filter(t)]
    st.write(f"Transactions found: {len(found)}")

    st.subheader("Maybe: safe_category")
    # safe_category returns Maybe.nothing() for an id that does not exist,
    # so map/get_or_else handle a missing category without try/except.
    maybe_cat_id = st.text_input("Category id to look up", value="food")
    cat_name = (
        safe_category(categories, maybe_cat_id)
        .map(lambda c: c.name)
        .get_or_else("(not found)")
    )
    st.write(f"Category name: {cat_name}")

    st.subheader("compose / pipe")
    # Two small functions, chained with compose (right to left) and
    # pipe (left to right). Both give the same result for the same order.
    to_positive = abs
    double = lambda x: x * 2
    demo_amount = st.number_input("Amount to transform", value=-5000, step=500)
    composed = compose(double, to_positive)(int(demo_amount))
    piped = pipe(int(demo_amount), to_positive, double)
    st.write(f"compose(double, abs)({int(demo_amount)}) = {composed}")
    st.write(f"pipe({int(demo_amount)}, abs, double) = {piped}")

elif page == "Pipelines":
    # Lab 2 task: expense report based on the category hierarchy.
    st.title("Pipelines")
    st.subheader("Category hierarchy report")

    roots = [c.id for c in categories if c.parent_id is None]
    root = st.selectbox("Root category", roots)

    tree = flatten_categories(categories, root)
    st.write("Categories in this tree:", [c.name for c in tree])

    total = sum_expenses_recursive(categories, transactions, root)
    st.metric(f"Total expenses in {root}", f"{total} KZT")

    st.subheader("Lazy stream of transactions")
    # iter_transactions is a generator: it yields matching transactions one
    # by one instead of building a full list. We simulate a "large stream"
    # by cycling the seed transactions repeat_by times, and only count how
    # many match - the stream is never fully materialized in memory.
    max_amount = st.slider("Only expenses smaller than", -50000, 0, -1000)
    repeat_by = st.number_input(
        "Repeat the seed data this many times (simulates a large stream)",
        min_value=1,
        value=100,
        step=50,
    )
    big_stream = itertools.chain.from_iterable(
        itertools.repeat(transactions, int(repeat_by))
    )
    matching = iter_transactions(big_stream, lambda t: t.amount <= max_amount)
    count = sum(1 for _ in matching)
    st.write(f"Stream size: {len(transactions) * int(repeat_by)} transactions")
    st.write(f"Matching transactions found: {count}")

elif page == "Reports":
    # Lab 3 task: memoized expense forecast with a cache speed demo.
    st.title("Reports")
    st.subheader("Forecast (cached)")

    cat_id = st.selectbox("Category", [c.id for c in categories], key="forecast_cat")
    period = st.number_input("Number of periods", min_value=1, value=3, step=1)

    result, before_ms, after_ms = measure_forecast(cat_id, transactions, int(period))
    st.metric(f"Forecast per period for {cat_id}", f"{result} KZT")
    st.write(f"First call (no cache): {before_ms:.4f} ms")
    st.write(f"Second call (cached): {after_ms:.4f} ms")

    st.subheader("Transaction validation pipeline")
    # Either.left_of carries the first problem found (bad account, bad
    # category, or an exceeded budget). No try/except in the happy path.
    t_id = st.selectbox("Transaction", [t.id for t in transactions], key="validate_t")
    picked = next(t for t in transactions if t.id == t_id)

    result = validate_transaction(picked, accounts, categories)
    budget = next((b for b in budgets if b.cat_id == picked.cat_id), None)
    if result.is_right and budget is not None:
        result = check_budget(budget, transactions).map(lambda _b: picked)

    if result.is_right:
        st.success(f"Transaction {t_id} is valid")
    else:
        st.error(f"Transaction {t_id} rejected: {result.left}")

    st.subheader("Lazy top categories")
    # Expenses stream lazily through iter_transactions, then
    # lazy_top_categories adds them up and yields only the top k.
    # The full totals dict is the only thing materialized, at the end.
    k = st.slider("How many top categories", 1, 5, 3)
    expenses = iter_transactions(transactions, lambda t: t.amount < 0)
    top = list(lazy_top_categories(expenses, categories, int(k)))
    for name, spent in top:
        st.write(f"{name}: {spent} KZT")

    st.subheader("Budget report (composed)")
    # BudgetService pipes a validator and a calculator (both pure,
    # injected in __init__) through the month, and shows each step.
    months = sorted({t.ts[:7] for t in transactions})
    month = st.selectbox("Month", months, key="budget_month")
    budget_service = BudgetService(
        validators=[make_budget_validator(budgets, transactions)],
        calculators=[make_spending_calculator(transactions)],
    )
    budget_report = budget_service.monthly_report(month)
    st.write("Steps:", budget_report["steps"])
    st.write("Spending per category:", budget_report["spending"])
    st.write("Budgets checked:", budget_report["budgets_checked"])

    st.subheader("Category report (composed)")
    # ReportService pipes one aggregator (also pure and injected) over
    # the picked category.
    report_cat_id = st.selectbox(
        "Category", [c.id for c in categories], key="report_service_cat"
    )
    report_service = ReportService(aggregators=[make_category_aggregator(transactions)])
    cat_report = report_service.category_report(report_cat_id)
    st.write("Steps:", cat_report["steps"])
    st.write(f"Total: {cat_report['total']} KZT, count: {cat_report['count']}")

elif page == "Async/FRP":
    # Lab 6 task: event bus with pure subscriber functions.
    st.title("Async/FRP")
    st.subheader("Event bus")

    if "bus" not in st.session_state:
        # First visit: build the bus and subscribe the pure handlers.
        # session_state keeps this same bus across Streamlit reruns.
        start_state = {
            "accounts": accounts,
            "budgets": budgets,
            "transactions": transactions,
            "notifications": (),
        }
        bus = EventBus(start_state)
        bus.subscribe(TRANSACTION_ADDED, apply_transaction)
        bus.subscribe(TRANSACTION_ADDED, check_budget_after_transaction)
        bus.subscribe(BUDGET_ALERT, on_budget_alert)
        bus.subscribe(BALANCE_ALERT, on_balance_alert)
        st.session_state.bus = bus

    bus = st.session_state.bus

    acc_id = st.selectbox("Account", [a.id for a in accounts], key="frp_acc")
    cat_id = st.selectbox("Category", [c.id for c in categories], key="frp_cat")
    amount = st.number_input(
        "Transaction amount", value=-5000, step=1000, key="frp_amt"
    )

    col1, col2, col3 = st.columns(3)
    if col1.button("Publish TRANSACTION_ADDED"):
        new_t = Transaction(
            f"t_evt_{len(bus.state['transactions'])}",
            acc_id,
            cat_id,
            int(amount),
            "2026-09-17",
            "FRP demo",
        )
        bus.publish(TRANSACTION_ADDED, {"transaction": new_t})
    if col2.button("Publish BUDGET_ALERT"):
        bus.publish(BUDGET_ALERT, {"message": f"Manual budget alert for {cat_id}"})
    if col3.button("Publish BALANCE_ALERT"):
        bus.publish(BALANCE_ALERT, {"message": f"Low balance warning for {acc_id}"})

    st.subheader("Live account balances")
    for a in bus.state["accounts"]:
        st.write(f"{a.name}: {a.balance} KZT")

    st.subheader("Live alerts")
    if bus.state["notifications"]:
        for n in bus.state["notifications"]:
            st.write(n)
    else:
        st.write("No alerts yet.")

else:
    # Menu items for the next labs.
    st.title(page)
    st.info("This part will be added in a later lab.")
