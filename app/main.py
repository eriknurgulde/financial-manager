# Streamlit web app. Start it from the project folder:
#     streamlit run app/main.py

import sys
from dataclasses import asdict
from pathlib import Path

import streamlit as st

# Streamlit starts from the app/ folder, so Python can not see core/.
# We add the project folder to the import path to fix this.
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from core.domain import Transaction
from core.transforms import (
    account_balance,
    add_transaction,
    load_seed,
    total_balance,
    update_budget,
)

# All menu items required by the task. Labs 2-8 will fill the empty ones.
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

else:
    # Menu items for the next labs.
    st.title(page)
    st.info("This part will be added in a later lab.")
