# Service facades for Lab 7.
# BudgetService and ReportService do not hold data themselves. They get
# a list of pure "step" functions (validators/calculators/aggregators)
# injected in __init__, and just pipe a small state dict through them.
# Each step function is a closure built from the app's data (see the
# make_* functions below), so the services stay generic and testable.

from core.compose import pipe
from core.ftypes import check_budget


def make_budget_validator(budgets, transactions):
    # Closure: checks every budget against this month's transactions.
    def validate(state: dict) -> dict:
        month = state["month"]
        checked = []
        for b in budgets:
            month_trans = tuple(
                t
                for t in transactions
                if t.ts.startswith(month) and t.cat_id == b.cat_id
            )
            result = check_budget(b, month_trans)
            checked.append({"budget_id": b.id, "ok": result.is_right})
        return {
            **state,
            "budgets_checked": tuple(checked),
            "steps": state["steps"] + ("validated budgets for the month",),
        }

    return validate


def make_spending_calculator(transactions):
    # Closure: totals this month's expenses per category.
    def calculate(state: dict) -> dict:
        month = state["month"]
        totals: dict[str, int] = {}
        for t in transactions:
            if t.ts.startswith(month) and t.amount < 0:
                totals[t.cat_id] = totals.get(t.cat_id, 0) - t.amount
        return {
            **state,
            "spending": totals,
            "steps": state["steps"] + ("calculated spending per category",),
        }

    return calculate


class BudgetService:
    def __init__(self, validators, calculators):
        self.validators = validators
        self.calculators = calculators

    def monthly_report(self, month: str) -> dict:
        # Compose validators then calculators into one pipeline.
        start = {"month": month, "steps": ()}
        return pipe(start, *self.validators, *self.calculators)


def make_category_aggregator(transactions):
    # Closure: totals and counts transactions of one category.
    def aggregate(state: dict) -> dict:
        cat_id = state["cat_id"]
        cat_trans = tuple(t for t in transactions if t.cat_id == cat_id)
        total = sum(t.amount for t in cat_trans)
        return {
            **state,
            "total": total,
            "count": len(cat_trans),
            "steps": state["steps"] + ("aggregated the category's transactions",),
        }

    return aggregate


class ReportService:
    def __init__(self, aggregators):
        self.aggregators = aggregators

    def category_report(self, cat_id: str) -> dict:
        start = {"cat_id": cat_id, "steps": ()}
        return pipe(start, *self.aggregators)
