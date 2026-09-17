# Maybe and Either containers for Lab 4.
# They let the caller chain map/bind/get_or_else instead of using
# try/except in the "happy path" when a value may be missing or invalid.

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from core.domain import Account, Budget, Category, Transaction

A = TypeVar("A")
B = TypeVar("B")
E = TypeVar("E")


@dataclass(frozen=True)
class Maybe(Generic[A]):
    # Holds a value (has_value=True) or nothing (has_value=False).
    value: A | None
    has_value: bool

    @staticmethod
    def some(value: A) -> "Maybe[A]":
        return Maybe(value, True)

    @staticmethod
    def nothing() -> "Maybe[A]":
        return Maybe(None, False)

    def map(self, func: Callable[[A], B]) -> "Maybe[B]":
        # Apply func only if there is a value, otherwise stay empty.
        if not self.has_value:
            return Maybe.nothing()
        return Maybe.some(func(self.value))

    def bind(self, func: Callable[[A], "Maybe[B]"]) -> "Maybe[B]":
        # Like map, but func itself returns a Maybe (no Maybe[Maybe[B]]).
        if not self.has_value:
            return Maybe.nothing()
        return func(self.value)

    def get_or_else(self, default: A) -> A:
        return self.value if self.has_value else default


@dataclass(frozen=True)
class Either(Generic[E, A]):
    # Holds an error in left, or a good value in right, never both.
    left: E | None
    right: A | None
    is_right: bool

    @staticmethod
    def right_of(value: A) -> "Either[E, A]":
        return Either(None, value, True)

    @staticmethod
    def left_of(error: E) -> "Either[E, A]":
        return Either(error, None, False)

    def map(self, func: Callable[[A], B]) -> "Either[E, B]":
        if not self.is_right:
            return Either.left_of(self.left)
        return Either.right_of(func(self.right))

    def bind(self, func: Callable[[A], "Either[E, B]"]) -> "Either[E, B]":
        if not self.is_right:
            return Either.left_of(self.left)
        return func(self.right)

    def get_or_else(self, default: A) -> A:
        return self.right if self.is_right else default


def safe_category(cats: tuple[Category, ...], cat_id: str) -> Maybe[Category]:
    # Find a category by id, or Nothing if it does not exist.
    found = [c for c in cats if c.id == cat_id]
    return Maybe.some(found[0]) if found else Maybe.nothing()


def validate_transaction(
    t: Transaction, accs: tuple[Account, ...], cats: tuple[Category, ...]
) -> Either[dict, Transaction]:
    # Check the account exists, then the category exists.
    # First problem found becomes the Left error.
    acc_ok = any(a.id == t.account_id for a in accs)
    if not acc_ok:
        return Either.left_of({"error": "account not found", "account_id": t.account_id})

    cat = safe_category(cats, t.cat_id)
    if not cat.has_value:
        return Either.left_of({"error": "category not found", "cat_id": t.cat_id})

    return Either.right_of(t)


def check_budget(b: Budget, trans: tuple[Transaction, ...]) -> Either[dict, Budget]:
    # Right if spending on the budget's category is within the limit.
    spent = -sum(t.amount for t in trans if t.cat_id == b.cat_id and t.amount < 0)
    if spent > b.limit:
        return Either.left_of(
            {"error": "budget exceeded", "cat_id": b.cat_id, "spent": spent, "limit": b.limit}
        )
    return Either.right_of(b)
