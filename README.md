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
core/ftypes.py        - Maybe/Either containers (Lab 4)
core/lazy.py          - generators for lazy evaluation (Lab 5)
core/frp.py            - event bus and pure subscribers (Lab 6)
core/compose.py        - compose / pipe (Lab 7)
core/service.py        - BudgetService / ReportService facades (Lab 7)
data/seed.json       - test data
tests/test_lab1.py   - tests for Lab 1
tests/test_lab2.py   - tests for Lab 2
tests/test_lab3.py   - tests for Lab 3
tests/test_lab4.py   - tests for Lab 4
tests/test_lab5.py   - tests for Lab 5
tests/test_lab6.py   - tests for Lab 6
tests/test_lab7.py   - tests for Lab 7
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

## Lab 4 - Functional Patterns: Maybe/Either

Menu: **Functional Core** (Maybe), **Reports** (validation pipeline)

| Function | What it does |
|---|---|
| `Maybe.some(x)` / `Maybe.nothing()` | Container for a value that may be missing, with `map`, `bind`, `get_or_else` |
| `Either.right_of(x)` / `Either.left_of(e)` | Container for a good value or an error, with `map`, `bind`, `get_or_else` |
| `safe_category(cats, cat_id)` | Looks up a category, returns `Maybe[Category]` |
| `validate_transaction(t, accs, cats)` | Checks account and category exist, returns `Either[dict, Transaction]` |
| `check_budget(b, trans)` | Checks a budget is not exceeded, returns `Either[dict, Budget]` |

In **Functional Core**, type a category id to see `safe_category` handle a
missing category through `Maybe` (no try/except). In **Reports**, pick a
transaction to run it through the validation pipeline (account exists,
category is valid, budget not exceeded) and see the `Either` result.

## Lab 5 - Lazy Evaluation

Menu: **Pipelines** (lazy stream demo), **Reports** (lazy top categories)

| Function | What it does |
|---|---|
| `iter_transactions(trans, pred)` | Generator: yields transactions matching `pred`, one at a time |
| `lazy_top_categories(trans, cats, k)` | Generator: streams expenses, yields only the top `k` categories |

In **Pipelines**, pick an amount threshold and a repeat count to build a
big simulated transaction stream, then see how many match - the stream is
never turned into a full list. In **Reports**, pick how many top
categories to show; expenses are streamed through `iter_transactions`
into `lazy_top_categories`, and the list is only built at the very end.

## Lab 6 - FRP / Event Processing

Menu: **Async/FRP**

| Function | What it does |
|---|---|
| `Event(name, ts, payload)` | NamedTuple: one thing that happened in the app |
| `EventBus.subscribe(name, handler)` | Registers a pure handler for an event name |
| `EventBus.publish(name, payload)` | Builds an `Event` and runs its handlers |
| `apply_transaction(event, state)` | Adds a transaction and updates the account balance |
| `check_budget_after_transaction(event, state)` | Adds a notification if the budget was exceeded |
| `on_budget_alert` / `on_balance_alert` | Turn an alert event into a notification |

Handlers are pure: they take `(event, state)` and return a new state, they
never change anything in place. Only the bus keeps the current state.

In **Async/FRP**, pick an account, category and amount, then publish a
`TRANSACTION_ADDED`, `BUDGET_ALERT` or `BALANCE_ALERT` event and watch the
live account balances and alerts update below.

## Lab 7 - Composition / Modularity + OOP Integration

Menu: **Functional Core** (compose/pipe), **Reports** (service facades)

| Function | What it does |
|---|---|
| `compose(*funcs)` | Chains functions right to left: `compose(f, g)(x) == f(g(x))` |
| `pipe(x, *funcs)` | Chains functions left to right: `pipe(x, f, g) == g(f(x))` |
| `BudgetService(validators, calculators)` | Facade: pipes injected pure steps into `monthly_report(month)` |
| `ReportService(aggregators)` | Facade: pipes injected pure steps into `category_report(cat_id)` |

The services do not hold any data themselves - `make_budget_validator`,
`make_spending_calculator` and `make_category_aggregator` (in
`core/service.py`) are closures built from the app's data and injected
into the service through `__init__` (dependency injection).

In **Functional Core**, pick an amount to see `compose` and `pipe` give
the same result for the same function order. In **Reports**, pick a
month or a category to see the service pipeline and its steps.

## Team

| Member | GitHub |
|---|---|
| Yeskendir | [@eriknurgulde](https://github.com/eriknurgulde) |
| Dimasena | [@Dimasena](https://github.com/Dimasena) |
| Zhangir | [@zhangir777](https://github.com/zhangir777) |
