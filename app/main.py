# Streamlit web app. Start it from the project folder:
#     streamlit run app/main.py

import asyncio
import itertools
import re
import sys
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

import streamlit as st

# Streamlit starts from the app/ folder, so Python can not see core/.
# We add the project folder to the import path to fix this.
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from core.async_ops import balance_forecast, build_final_report, expenses_by_month
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
from core.report import budget_status, income_and_expenses, spending_by_category
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

# The newest date in the data. The demos use it for "new" transactions,
# so they land in the last month of the data.
LAST_DATE = max(t.ts for t in transactions)

# Categories without children. Money is booked on these, so the demos that
# look at one category (forecast, report, new transaction) offer only them.
LEAF_IDS = [c.id for c in categories if all(x.parent_id != c.id for x in categories)]

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

    # Analytics: income vs expenses for all the data.
    income, spent = income_and_expenses(transactions)
    col1, col2, col3 = st.columns(3)
    col1.metric("Income", f"{income} KZT")
    col2.metric("Expenses", f"{spent} KZT")
    col3.metric("Saved", f"{income - spent} KZT")

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
    new_t = Transaction("t_new", "acc1", "cafe", -5000, LAST_DATE, "Demo")
    new_list = add_transaction(transactions, new_t)
    # The old tuple did not change, we got a new one with one more item.
    st.write(f"Old tuple: {len(transactions)} items")
    st.write(f"New tuple: {len(new_list)} items")

    st.subheader("update_budget")
    new_limit = st.number_input(
        f"New limit for {budgets[0].id} ({budgets[0].cat_id})",
        value=budgets[0].limit + 10000,
        step=1000,
    )
    new_budgets = update_budget(budgets, budgets[0].id, int(new_limit))
    st.write(f"Old limit: {budgets[0].limit} KZT")
    st.write(f"New limit: {new_budgets[0].limit} KZT")

    # Lab 2 task: closures demo (by_category, by_amount_range).
    st.subheader("Closures: filters")
    cat_id = st.selectbox("Category", LEAF_IDS)
    min_a, max_a = st.slider("Amount range", -200000, 400000, (-200000, 400000))
    first_date = date.fromisoformat(min(t.ts for t in transactions))
    last_date = date.fromisoformat(LAST_DATE)
    d_from, d_to = st.date_input(
        "Date range",
        value=(first_date, last_date),
        min_value=first_date,
        max_value=last_date,
    )
    cat_filter = by_category(cat_id)
    amount_filter = by_amount_range(min_a, max_a)
    date_filter = by_date_range(d_from.isoformat(), d_to.isoformat())
    found = [
        t for t in transactions if cat_filter(t) and amount_filter(t) and date_filter(t)
    ]
    st.write(f"Transactions found: {len(found)}")
    st.dataframe([asdict(t) for t in found])

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
    max_amount = st.slider("Only expenses smaller than", -200000, 0, -5000)
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

    cat_id = st.selectbox("Category", LEAF_IDS, key="forecast_cat")
    # By default the periods are the months of the data, so the forecast is
    # the average spending per month.
    data_months = len({t.ts[:7] for t in transactions})
    period = st.number_input(
        "Number of periods (months)", min_value=1, value=data_months, step=1
    )

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
        # The limit is per month: check the month of this transaction.
        same_month = tuple(t for t in transactions if t.ts[:7] == picked.ts[:7])
        result = check_budget(budget, same_month).map(lambda _b: picked)

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
    month = st.selectbox("Month", months, index=len(months) - 1, key="budget_month")
    budget_service = BudgetService(
        validators=[make_budget_validator(budgets, transactions)],
        calculators=[make_spending_calculator(transactions)],
    )
    budget_report = budget_service.monthly_report(month)
    st.write("Steps:", budget_report["steps"])
    st.write("Spending per category:", budget_report["spending"])
    st.write("Budgets checked:", budget_report["budgets_checked"])

    # Highlight the budgets whose monthly limit is exceeded.
    for row in budget_status(budgets, transactions, month):
        text = f"{row['cat_id']}: {row['spent']} / {row['limit']} KZT"
        if row["exceeded"]:
            st.error(f"Budget exceeded - {text}")
        else:
            st.success(f"Within budget - {text}")

    st.subheader("Category report (composed)")
    # ReportService pipes one aggregator (also pure and injected) over
    # the picked category.
    report_cat_id = st.selectbox("Category", LEAF_IDS, key="report_service_cat")
    report_service = ReportService(aggregators=[make_category_aggregator(transactions)])
    cat_report = report_service.category_report(report_cat_id)
    st.write("Steps:", cat_report["steps"])
    st.write(f"Total: {cat_report['total']} KZT, count: {cat_report['count']}")

    st.subheader("Income vs expenses")
    income, spent = income_and_expenses(transactions)
    st.write(f"Income: {income} KZT, expenses: {spent} KZT")
    st.write("Expenses by category:")
    st.bar_chart(spending_by_category(transactions, categories))

    st.subheader("Final report (one click)")
    # Lab 8 end-to-end scenario: load -> filter -> lazy top categories ->
    # cached forecast per top category -> parallel monthly/account
    # totals (asyncio.gather), all built into one report dict.
    first_date = date.fromisoformat(min(t.ts for t in transactions))
    last_date = date.fromisoformat(LAST_DATE)
    report_from, report_to = st.date_input(
        "Report period",
        value=(first_date, last_date),
        min_value=first_date,
        max_value=last_date,
        key="final_period",
    )
    if st.button("Build final report"):
        final = build_final_report(
            accounts,
            categories,
            transactions,
            budgets,
            report_from.isoformat(),
            report_to.isoformat(),
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("Income", f"{final['income']} KZT")
        col2.metric("Expenses", f"{final['expenses']} KZT")
        col3.metric("Total balance", f"{sum(final['balances'].values())} KZT")
        st.write("Balance per account:", final["balances"])
        st.write("Balance forecast for next month:", final["balance_forecast"])
        st.write("Expenses by month:")
        st.bar_chart(final["expenses_by_month"])
        st.write(f"Budgets exceeded in {final['month']}:")
        if final["exceeded_budgets"]:
            for cat in final["exceeded_budgets"]:
                st.error(f"Budget exceeded: {cat}")
        else:
            st.success("No budget is exceeded.")
        st.write("Top categories:", final["top_categories"])
        st.write("Forecast per month for the top categories:", final["forecasts"])

elif page == "Async/FRP":
    # Lab 6 task: event bus with pure subscriber functions.
    st.title("Async/FRP")
    st.subheader("Event bus")

    if "bus" not in st.session_state:
        # First visit: build the bus and subscribe the pure handlers.
        # session_state keeps this same bus across Streamlit reruns.
        # Accounts hold the START money, so add the transactions to get
        # the balance each account has today.
        current = tuple(
            replace(a, balance=a.balance + account_balance(transactions, a.id))
            for a in accounts
        )
        start_state = {
            "accounts": current,
            "budgets": budgets,
            "transactions": transactions,
            "notifications": (),
        }
        bus = EventBus(start_state)
        bus.subscribe(TRANSACTION_ADDED, apply_transaction)
        bus.subscribe(TRANSACTION_ADDED, check_budget_after_transaction)
        bus.subscribe(TRANSACTION_ADDED, check_balance_after_transaction)
        bus.subscribe(BUDGET_ALERT, on_budget_alert)
        bus.subscribe(BALANCE_ALERT, on_balance_alert)
        st.session_state.bus = bus

    bus = st.session_state.bus

    acc_id = st.selectbox("Account", [a.id for a in accounts], key="frp_acc")
    cat_id = st.selectbox("Category", LEAF_IDS, key="frp_cat")
    amount = st.number_input(
        "Transaction amount", value=-5000, step=1000, key="frp_amt"
    )
    st.caption(
        "Try a big expense on Cash: the balance drops below 10000 KZT and "
        "a low-balance alert appears. Many cafe expenses trigger a budget alert."
    )

    col1, col2, col3 = st.columns(3)
    if col1.button("Publish TRANSACTION_ADDED"):
        new_t = Transaction(
            f"t_evt_{len(bus.state['transactions'])}",
            acc_id,
            cat_id,
            int(amount),
            LAST_DATE,
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

    st.subheader("Async aggregations")
    # expenses_by_month and balance_forecast run one coroutine per month
    # (or per account) and asyncio.gather runs them all together.
    months = sorted({t.ts[:7] for t in transactions})
    monthly = asyncio.run(expenses_by_month(list(transactions), months))
    st.write("Expenses by month:", monthly)
    balances = asyncio.run(balance_forecast(list(accounts), list(transactions)))
    st.write("Balance forecast per account:", balances)

elif page == "Tests":
    # No lab task uses this page - it just points to the test suite.
    st.title("Tests")
    st.write("Run the test suite from the project folder:")
    st.code("pytest -q")

    # Count the test functions in every tests/test_lab*.py file.
    counts = {
        f.name: len(
            re.findall(r"^def test_", f.read_text(encoding="utf-8"), re.MULTILINE)
        )
        for f in sorted((ROOT / "tests").glob("test_lab*.py"))
    }
    for name, count in counts.items():
        st.write(f"`tests/{name}`: {count} tests")
    st.write(f"**Total: {sum(counts.values())} tests.**")

else:
    # page == "About" - no lab task uses this page either.
    st.title("About")
    st.write(
        "Financial Manager is a personal finance app (accounts, "
        "categories, transactions, budgets) written in Python in a "
        "functional style: pure functions, immutability, recursion, "
        "lazy evaluation, FRP and async."
    )
    st.subheader("Team")
    st.write("- Erik Nurgulde")
    st.write("- Dimasena")
    st.write("- Zhangir")
