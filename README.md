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
app/main.py          - the web page (menu and screens)
core/domain.py       - data models (read-only / immutable)
core/transforms.py   - pure functions and closures
core/recursion.py    - category tree recursion (Lab 2)
core/memo.py          - memoized forecast (Lab 3)
data/seed.json       - test data
tests/test_lab1.py   - tests for Lab 1
tests/test_lab2.py   - tests for Lab 2
tests/test_lab3.py   - tests for Lab 3
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

## Lab 2 - Lambda and Closures + Recursion

Menu: **Functional Core** (closures), **Pipelines** (category tree report)

| Function | What it does |
|---|---|
| `by_category(cat_id)` | Closure: returns a filter for one category |
| `by_date_range(start, end)` | Closure: returns a filter for a date range |
| `by_amount_range(min, max)` | Closure: returns a filter for an amount range |
| `flatten_categories(cats, root)` | Recursive: root category + all its children |
| `sum_expenses_recursive(cats, trans, root_id)` | Recursive: total expenses of a category tree |

In **Functional Core**, pick a category and an amount range to see the
closures filter transactions. In **Pipelines**, pick a root category
(Food, Transport, Leisure, Income) to see its full tree and total
expenses.

## Lab 3 - Advanced Recursion + Memoization

Menu: **Reports** (Forecast (cached))

| Function | What it does |
|---|---|
| `forecast_expenses(cat_id, trans, period)` | Memoized (`lru_cache`): average expense per period for a category |
| `measure_forecast(cat_id, trans, period)` | Runs the forecast cold and cached, returns both times in ms |

In **Reports**, pick a category and a number of periods to see the
forecast, plus how much faster the second (cached) call is compared to
the first one.

## Team

| Member | GitHub |
|---|---|
| Yeskendir | [@eriknurgulde](https://github.com/eriknurgulde) |
| Dimasena | [@Dimasena](https://github.com/Dimasena) |
| Zhangir | [@zhangir777](https://github.com/zhangir777) |
