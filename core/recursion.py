# Recursive functions for the category tree.
# A category can have child categories (parent_id points to it).
# Recursion lets us walk down the tree without knowing its depth.

from core.domain import Category, Transaction


def flatten_categories(cats: tuple[Category, ...], root: str) -> tuple[Category, ...]:
    # Return the root category plus all its children, grandchildren, etc.
    # Base case: no direct children -> just the root category (or nothing
    # if root id is not found).
    root_cat = tuple(filter(lambda c: c.id == root, cats))
    children = tuple(filter(lambda c: c.parent_id == root, cats))

    # Recursive case: flatten each child subtree and join everything.
    result = root_cat
    for child in children:
        result = result + flatten_categories(cats, child.id)
    return result


def sum_expenses_recursive(
    cats: tuple[Category, ...], trans: tuple[Transaction, ...], root_id: str
) -> int:
    # Sum the expenses of a category and of all its child categories.
    # Expenses are stored as negative amounts, so we return a positive total.
    ids = tuple(c.id for c in flatten_categories(cats, root_id))
    own = filter(lambda t: t.cat_id in ids and t.amount < 0, trans)
    return -sum(t.amount for t in own)
