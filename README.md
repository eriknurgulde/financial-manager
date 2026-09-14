# Financial Manager

A single-page web application for managing personal finances — transactions, categories,
budgets, accounts, events and reports — written in a **functional programming style**:
pure functions, immutable data, composition, recursion, lazy evaluation, FRP and async.

Python 3.11+ · Streamlit · pytest · black · ruff

---

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
streamlit run app/main.py
```

The app opens at <http://localhost:8501>.

### Checks

```bash
pytest -q          # 70 tests
ruff check .       # lint
black --check .    # formatting
```

All three run automatically on every pull request via GitHub Actions.

---

## Navigating the app

The **sidebar is the burger menu** — on a narrow screen Streamlit collapses it behind the
hamburger icon in the top-left corner.

| Menu item           | Status   | What is there                                                                                  |
| ------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| **Overview**        | Lab 1    | Accounts, categories, transactions, total balance, income vs expenses, top spending categories |
| **Data**            | Lab 1    | The loaded dataset: accounts, the category tree, a filterable transaction table, budgets       |
| **Functional Core** | Lab 1    | The three Lab 1 functions, run live with before/after collections                              |
| Pipelines           | Lab 2–3  | —                                                                                              |
| Async/FRP           | Lab 6, 8 | —                                                                                              |
| Reports             | Lab 3–4  | —                                                                                              |
| Tests               | —        | How to run the suite                                                                           |
| About               | —        | Project layout and dataset summary                                                             |

Screens belonging to later labs say so rather than pretending to work.

---

## Project structure

```
financial-manager/
├── app/
│   └── main.py              # Streamlit page — the only module that draws or holds state
├── core/
│   ├── domain.py            # immutable entities (frozen dataclasses)
│   ├── transforms.py        # pure functions, HOF — the functional core
│   └── loader.py            # the single I/O boundary
├── data/
│   └── seed.json            # 3 accounts · 20 categories · 128 transactions · 5 budgets
├── tools/
│   └── generate_seed.py     # reproducible generator for seed.json
├── tests/
│   ├── test_domain.py       # 12 — immutability guarantees
│   ├── test_loader.py       # 16 — parsing and dataset integrity
│   ├── test_transforms.py   # 25 — the functional core
│   └── test_app.py          # 17 — the Streamlit page, via AppTest
├── pyproject.toml           # black, ruff and pytest configuration
└── requirements.txt
```

### Two conventions worth knowing

**Money is an `int` in minor units** (tiins; 1 KZT = 100 tiin). Adding up a hundred float
amounts accumulates rounding drift and produces balances like `249999.99999997`. Integers
stay exact. `format_money` renders them for display.

**Income is positive, expenses are negative.** That is why `account_balance` is a plain
`reduce` with no branching on the sign.

**`Account.balance` is the _opening_ balance** — what was on the account before the
transaction log begins. The specification gives `account_balance(trans, acc_id)` only the
transactions, so it can only return the net movement. `current_balance(account, trans)`
adds the two, and that is what Overview reports as the total balance.

---

## Lab 1 — Pure Functions · Immutability · HOF

**Menu:** Overview · Data · Functional Core

### The required functions

| Function                                 | Module               | Notes                                                                  |
| ---------------------------------------- | -------------------- | ---------------------------------------------------------------------- |
| `load_seed(path)`                        | `core/loader.py`     | Reads the JSON and returns four immutable tuples                       |
| `add_transaction(trans, t)`              | `core/transforms.py` | Returns `(*trans, t)` — a new tuple                                    |
| `update_budget(budgets, bid, new_limit)` | `core/transforms.py` | `map` + `dataclasses.replace`; an unknown `bid` returns an equal tuple |
| `account_balance(trans, acc_id)`         | `core/transforms.py` | `reduce(add, map(..., filter(...)), 0)`                                |

```python
from core.loader import load_seed
from core.transforms import account_balance, add_transaction, update_budget

accounts, categories, transactions, budgets = load_seed("data/seed.json")

account_balance(transactions, "a_kaspi")          # net movement, in tiins
longer = add_transaction(transactions, new_tx)    # transactions is unchanged
raised = update_budget(budgets, "b_food", 120_000 * 100)
```

### Why `load_seed` lives in `loader.py` and not `transforms.py`

Reading a file is a side effect. Putting it in `transforms.py` — described in the brief as
_pure functions_ — would compromise the one property the project is built on. So the
loader splits into three pieces:

- `read_seed_text(path)` — the **only** function in `core` that touches the disk
- `parse_seed(payload)` — **pure**, takes an already-decoded `dict`
- `load_seed(path)` — the composition of the two

The interesting logic is testable with no filesystem, and `core/transforms.py` stays 100%
pure.

### Acceptance criteria

| Requirement                                                                                 | Where                                                                             |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Models are immutable                                                                        | `core/domain.py` — all five are `@dataclass(frozen=True)`; `tests/test_domain.py` |
| Functions return new collections                                                            | `add_transaction`, `update_budget`; asserted in `tests/test_transforms.py`        |
| `map` / `filter` / `reduce` used                                                            | `core/transforms.py` throughout                                                   |
| `data/seed.json`: ≥3 accounts, ≥10 categories with hierarchy, ≥100 transactions, ≥3 budgets | 3 / 20 / 128 / 5 — checked by `tests/test_loader.py`                              |
| Overview shows counts and total balance                                                     | `app/main.py`, Overview                                                           |
| At least 5 tests                                                                            | **70**                                                                            |

### The dataset

`data/seed.json` is generated, not hand-written:

```bash
python tools/generate_seed.py
```

The RNG is seeded with a constant, so the file is reproduced byte for byte. Spending is
weighted — groceries and coffee frequent, travel rare — and salary, rent and utilities
recur monthly, so reports in later labs have a realistic shape.

### One ruff rule is disabled

`C417` asks for `map()`/`filter()` to be rewritten as generator expressions. The Lab 1
acceptance criteria require `map`/`filter`/`reduce` explicitly, so the rule is switched off
for `core/transforms.py` only — every other file still has it. See `pyproject.toml`.

---

## Roadmap

| Lab   | Topic                                   | Menu                                  |
| ----- | --------------------------------------- | ------------------------------------- |
| **1** | **Pure functions · immutability · HOF** | **Overview · Data · Functional Core** |
| 2     | Lambdas, closures, recursion            | Functional Core · Pipelines           |
| 3     | Advanced recursion, memoization         | Pipelines · Reports                   |
| 4     | Maybe / Either                          | Functional Core · Reports             |
| 5     | Lazy evaluation                         | Pipelines · Reports                   |
| 6     | FRP, event bus                          | Async/FRP                             |
| 7     | Composition, modularity, DI             | Functional Core · Pipelines · Reports |
| 8     | Async, parallelism, final integration   | Async/FRP · Reports                   |

---

## Team

| Member        | GitHub                                           | Lab 1 contribution                                                                                |
| ------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| Erik Nurgulde | [@eriknurgulde](https://github.com/eriknurgulde) | Repository setup, initial project structure                                                       |
| Dimasena      | [@Dimasena](https://github.com/Dimasena)         | Code review, manual testing, and quality assurance for Lab 1                                      |
| Zhangir       | [@zhangir777](https://github.com/zhangir777)     | Tooling and CI, domain models, seed dataset and loader, functional core, Streamlit UI, test suite |

Code review for `lab-01` is requested from @eriknurgulde and @Dimasena.

### How we work

Each lab is submitted as a separate pull request (`lab-01`, `lab-02`, …) with a short
screencast. Work lands on the lab branch through small feature branches, one pull request
each, so every piece gets reviewed on its own:

```
feat/<something>  ->  lab-0N  ->  main
```

`ruff`, `black` and `pytest` run on every pull request; a red build blocks the merge.
