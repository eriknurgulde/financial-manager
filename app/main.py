"""Financial Manager - single-page Streamlit app.

Run from the repository root:

    streamlit run app/main.py

The sidebar is the burger menu: on a narrow screen Streamlit collapses it
behind the hamburger icon in the top-left corner. All eight menu items from the
brief are present; the ones belonging to later labs say so instead of pretending
to work.

This module is the only place allowed to hold state or draw things. Every number
on screen comes from a pure function in `core.transforms`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# `streamlit run app/main.py` puts app/ on sys.path, not the project root, so
# `core` would not be importable without this.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.domain import Transaction  # noqa: E402
from core.loader import DEFAULT_SEED_PATH, load_seed  # noqa: E402
from core.transforms import (  # noqa: E402
    account_balance,
    add_transaction,
    current_balance,
    expenses_by_category,
    find_category,
    format_money,
    overview,
    total_expenses,
    total_income,
    update_budget,
    where,
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

LAB_OF = {
    "Pipelines": "Lab 2-3",
    "Async/FRP": "Lab 6 and 8",
    "Reports": "Lab 3-4",
    "Tests": "Lab 1 onwards",
}


@st.cache_data
def get_seed():
    """Load the dataset once per session."""
    return load_seed(DEFAULT_SEED_PATH)


def category_label(cats, cat_id: str) -> str:
    """`Food / Coffee` for a child, plain `Food` for a root."""
    cat = find_category(cats, cat_id)
    if cat is None:
        return cat_id
    if cat.parent_id is None:
        return cat.name
    parent = find_category(cats, cat.parent_id)
    return f"{parent.name} / {cat.name}" if parent else cat.name


# --------------------------------------------------------------------------
# Menu items
# --------------------------------------------------------------------------


def render_overview(accounts, cats, trans, budgets) -> None:
    st.header("Overview")
    st.caption(
        "Every figure below is computed by a pure function in `core.transforms`."
    )

    stats = overview(accounts, cats, trans)

    a, b, c, d = st.columns(4)
    a.metric("Accounts", stats["accounts"])
    b.metric("Categories", stats["categories"])
    c.metric("Transactions", stats["transactions"])
    d.metric("Total balance", format_money(stats["total_balance"]))

    st.divider()

    left, right = st.columns(2)
    left.metric("Income", format_money(total_income(trans)))
    right.metric("Expenses", format_money(total_expenses(trans)))

    st.subheader("Per account")
    st.caption(
        "`balance` is the opening balance, `movement` is `account_balance(trans, id)`, "
        "and `current` is the two added together."
    )
    st.dataframe(
        [
            {
                "Account": a.name,
                "Opening": format_money(a.balance, a.currency),
                "Movement": format_money(account_balance(trans, a.id), a.currency),
                "Current": format_money(current_balance(a, trans), a.currency),
            }
            for a in accounts
        ],
        hide_index=True,
        width="stretch",
    )

    st.subheader("Where the money goes")
    spend = expenses_by_category(trans)
    if spend:
        ranked = sorted(spend.items(), key=lambda kv: kv[1], reverse=True)[:10]
        st.bar_chart(
            {category_label(cats, cid): amount / 100 for cid, amount in ranked},
            horizontal=True,
        )
        st.caption(
            "Top 10 categories by spend, in KZT. Direct hits only - rolling "
            "child categories into their parent is Lab 2."
        )

    st.subheader("Budgets")
    st.dataframe(
        [
            {
                "Budget": b.id,
                "Category": category_label(cats, b.cat_id),
                "Period": b.period,
                "Limit": format_money(b.limit),
                "Spent (all time)": format_money(spend.get(b.cat_id, 0)),
            }
            for b in budgets
        ],
        hide_index=True,
        width="stretch",
    )


def render_data(accounts, cats, trans, budgets) -> None:
    st.header("Data")
    st.caption(f"Loaded from `{DEFAULT_SEED_PATH.relative_to(ROOT).as_posix()}`.")

    tab_acc, tab_cat, tab_tx, tab_budget = st.tabs(
        ["Accounts", "Categories", "Transactions", "Budgets"]
    )

    with tab_acc:
        st.dataframe(
            [
                {
                    "id": a.id,
                    "name": a.name,
                    "opening balance": format_money(a.balance, a.currency),
                    "currency": a.currency,
                }
                for a in accounts
            ],
            hide_index=True,
            width="stretch",
        )

    with tab_cat:
        roots = [c for c in cats if c.parent_id is None]
        st.write(f"{len(cats)} categories, {len(roots)} of them roots.")
        for root in roots:
            children = [c for c in cats if c.parent_id == root.id]
            bullet = "\n".join(f"- {c.name} (`{c.id}`)" for c in children)
            st.markdown(f"**{root.name}** · `{root.type}`\n{bullet}")

    with tab_tx:
        st.write(f"{len(trans)} transactions.")
        kind = st.radio(
            "Show", ["All", "Income only", "Expenses only"], horizontal=True
        )
        predicate = {
            "All": lambda t: True,
            "Income only": lambda t: t.amount > 0,
            "Expenses only": lambda t: t.amount < 0,
        }[kind]
        shown = where(trans, predicate)
        st.caption(
            f"`where(trans, predicate)` returned {len(shown)} of {len(trans)} rows "
            "as a new tuple - the original is unchanged."
        )
        st.dataframe(
            [
                {
                    "id": t.id,
                    "date": t.ts.replace("T", " "),
                    "account": t.account_id,
                    "category": category_label(cats, t.cat_id),
                    "amount": format_money(t.amount),
                    "note": t.note,
                }
                for t in shown
            ],
            hide_index=True,
            width="stretch",
            height=420,
        )

    with tab_budget:
        st.dataframe(
            [
                {
                    "id": b.id,
                    "category": category_label(cats, b.cat_id),
                    "limit": format_money(b.limit),
                    "period": b.period,
                }
                for b in budgets
            ],
            hide_index=True,
            width="stretch",
        )


def render_functional_core(accounts, cats, trans, budgets) -> None:
    st.header("Functional Core")
    st.caption(
        "The three Lab 1 functions, run live. Each one returns a **new** collection - "
        "the loaded data never changes, which you can see in the before/after numbers."
    )

    st.subheader("`account_balance(trans, acc_id)`")
    st.code("reduce(add, map(lambda t: t.amount, filter(by_account, trans)), 0)")
    acc = st.selectbox(
        "Account", accounts, format_func=lambda a: f"{a.name} ({a.id})", key="ab"
    )
    if acc is not None:
        movement = account_balance(trans, acc.id)
        n = len(where(trans, lambda t: t.account_id == acc.id))
        c1, c2, c3 = st.columns(3)
        c1.metric("Transactions", n)
        c2.metric("Movement", format_money(movement, acc.currency))
        c3.metric(
            "Current balance", format_money(current_balance(acc, trans), acc.currency)
        )

    st.divider()

    st.subheader("`add_transaction(trans, t)`")
    st.code("return (*trans, t)")
    with st.form("add_tx"):
        col1, col2 = st.columns(2)
        form_acc = col1.selectbox(
            "Account", accounts, format_func=lambda a: a.name, key="add_acc"
        )
        form_cat = col2.selectbox(
            "Category", cats, format_func=lambda c: category_label(cats, c.id)
        )
        amount_kzt = st.number_input(
            "Amount in KZT (positive = income, negative = expense)",
            value=-2_500,
            step=500,
        )
        note = st.text_input("Note", value="Demo transaction")
        submitted = st.form_submit_button("Add")

    if submitted and form_acc is not None and form_cat is not None:
        new_tx = Transaction(
            id=f"t{len(trans) + 1:04d}",
            account_id=form_acc.id,
            cat_id=form_cat.id,
            amount=int(amount_kzt) * 100,
            ts="2026-09-12T12:00:00",
            note=note,
        )
        extended = add_transaction(trans, new_tx)

        c1, c2 = st.columns(2)
        c1.metric("Original tuple", f"{len(trans)} transactions")
        c2.metric("Returned tuple", f"{len(extended)} transactions", delta="+1")
        st.success(
            f"Balance of **{form_acc.name}** would go from "
            f"{format_money(current_balance(form_acc, trans))} to "
            f"{format_money(current_balance(form_acc, extended))}."
        )
        st.info(
            "The loaded data is still "
            f"{len(trans)} transactions - `add_transaction` built a new tuple "
            "rather than appending to the old one."
        )

    st.divider()

    st.subheader("`update_budget(budgets, bid, new_limit)`")
    st.code(
        "tuple(\n"
        "    map(\n"
        "        lambda b: replace(b, limit=new_limit) if b.id == bid else b,\n"
        "        budgets,\n"
        "    )\n"
        ")"
    )
    budget = st.selectbox(
        "Budget",
        budgets,
        format_func=lambda b: f"{b.id} - {category_label(cats, b.cat_id)}",
    )
    if budget is not None:
        new_limit_kzt = st.slider(
            "New limit, KZT",
            min_value=1_000,
            max_value=300_000,
            value=budget.limit // 100,
            step=1_000,
        )
        updated = update_budget(budgets, budget.id, int(new_limit_kzt) * 100)
        st.dataframe(
            [
                {
                    "id": b.id,
                    "category": category_label(cats, b.cat_id),
                    "limit before": format_money(old.limit),
                    "limit after": format_money(b.limit),
                    "changed": "yes" if old.limit != b.limit else "",
                }
                for old, b in zip(budgets, updated, strict=True)
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Only the selected row changes. The other budgets are the same objects, "
            "and the original tuple still holds the old limit."
        )


def render_placeholder(name: str) -> None:
    st.header(name)
    st.info(f"Planned for {LAB_OF.get(name, 'a later lab')}. Not implemented yet.")


def render_tests() -> None:
    st.header("Tests")
    st.write(
        "The suite runs outside the app. From the repository root, with the "
        "virtual environment active:"
    )
    st.code("pytest -q\nruff check .\nblack --check .", language="bash")
    st.write(
        "Lab 1 ships **52 tests** across three files: `tests/test_domain.py` "
        "(immutability), `tests/test_loader.py` (parsing and the shipped dataset) "
        "and `tests/test_transforms.py` (the functional core)."
    )


def render_about(accounts, cats, trans, budgets) -> None:
    st.header("About")
    st.write(
        "**Financial Manager** - personal finances in a functional style: pure "
        "functions, immutable data, and composition."
    )
    st.write(
        f"Dataset: **{len(accounts)}** accounts, **{len(cats)}** categories, "
        f"**{len(trans)}** transactions, **{len(budgets)}** budgets."
    )
    st.markdown("""
**Layout**

| path | what lives there |
|---|---|
| `core/domain.py` | immutable entities (frozen dataclasses) |
| `core/transforms.py` | pure functions - the functional core |
| `core/loader.py` | the only place that touches the disk |
| `app/main.py` | this Streamlit page |
| `tools/generate_seed.py` | reproducible dataset generator |
| `tests/` | pytest suite |
""")
    st.caption("Team: Erik Nurgulde, Dimasena, Zhangir. Course project, Lab 1 of 8.")


# --------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Financial Manager", page_icon="💸", layout="wide")

    accounts, cats, trans, budgets = get_seed()

    with st.sidebar:
        st.title("💸 Financial Manager")
        choice = st.radio("Menu", MENU, label_visibility="collapsed")
        st.divider()
        st.caption(f"{len(trans)} transactions loaded")
        st.caption("Lab 1 - Pure Functions · Immutability · HOF")

    if choice == "Overview":
        render_overview(accounts, cats, trans, budgets)
    elif choice == "Data":
        render_data(accounts, cats, trans, budgets)
    elif choice == "Functional Core":
        render_functional_core(accounts, cats, trans, budgets)
    elif choice == "Tests":
        render_tests()
    elif choice == "About":
        render_about(accounts, cats, trans, budgets)
    else:
        render_placeholder(choice)


main()
