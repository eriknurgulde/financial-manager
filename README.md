# Financial Manager

A simple web app to manage personal money: accounts, categories,
transactions and budgets. Written in Python in a functional style.

## How to run

```bash
python -m venv .venv
.venv\Scripts\activate        # on Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

## How to check the code

```bash
pytest -q
ruff check .
black --check .
```

## Project structure

```
app/main.py         - the web page (menu and screens)
core/domain.py      - data models (read-only / immutable)
core/transforms.py  - pure functions for Lab 1
data/seed.json      - test data
tests/test_lab1.py  - tests for Lab 1
```

## Lab 1 - Pure Functions, Immutability, HOF

Menu: **Overview**, **Data**, **Functional Core**

| Function | What it does |
|---|---|
| `load_seed(path)` | Reads `seed.json` and returns tuples of models |
| `add_transaction(trans, t)` | Returns a new tuple with one more transaction |
| `update_budget(budgets, bid, new_limit)` | Returns new budgets where one budget has a new limit |
| `account_balance(trans, acc_id)` | Sums the transactions of one account with `filter`, `map`, `reduce` |

Data in `seed.json`: 3 accounts, 11 categories (Food, Transport, Leisure
with subcategories), 114 transactions, 3 budgets.

## Team

| Member | GitHub |
|---|---|
| Erik Nurgulde | [@eriknurgulde](https://github.com/eriknurgulde) |
| Dimasena | [@Dimasena](https://github.com/Dimasena) |
| Zhangir | [@zhangir777](https://github.com/zhangir777) |
