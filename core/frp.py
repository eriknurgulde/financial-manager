# FRP / event processing for Lab 6.
# EventBus is a small pub/sub hub. Handlers are pure functions:
# they take (event, state) and return a NEW state, they never mutate
# anything. Only the bus itself keeps the current state, like a box.

import time
from collections.abc import Callable
from dataclasses import replace

from core.domain import Event

TRANSACTION_ADDED = "TRANSACTION_ADDED"
BUDGET_ALERT = "BUDGET_ALERT"
BALANCE_ALERT = "BALANCE_ALERT"


class EventBus:
    def __init__(self, state: dict):
        self.state = state
        self.handlers: dict[str, list[Callable[[Event, dict], dict]]] = {}

    def subscribe(self, name: str, handler: Callable[[Event, dict], dict]) -> None:
        # Remember a handler for this event name.
        self.handlers.setdefault(name, []).append(handler)

    def publish(self, name: str, payload: dict) -> Event:
        # Build the event, then run every subscribed handler in order.
        # Each handler's result becomes the new state for the next one.
        event = Event(name, time.strftime("%Y-%m-%dT%H:%M:%S"), payload)
        for handler in self.handlers.get(name, []):
            self.state = handler(event, self.state)
        return event


def add_notification(state: dict, message: str) -> dict:
    # Helper: return a new state with one more notification.
    return {**state, "notifications": state["notifications"] + (message,)}


def apply_transaction(event: Event, state: dict) -> dict:
    # TRANSACTION_ADDED handler: add the transaction and update the
    # balance of the account it belongs to.
    t = event.payload["transaction"]
    new_trans = state["transactions"] + (t,)
    new_accounts = tuple(
        replace(a, balance=a.balance + t.amount) if a.id == t.account_id else a
        for a in state["accounts"]
    )
    return {**state, "transactions": new_trans, "accounts": new_accounts}


def check_budget_after_transaction(event: Event, state: dict) -> dict:
    # TRANSACTION_ADDED handler: warn if the transaction's category
    # went over its budget limit.
    t = event.payload["transaction"]
    budget = next((b for b in state["budgets"] if b.cat_id == t.cat_id), None)
    if budget is None:
        return state

    spent = -sum(
        x.amount for x in state["transactions"] if x.cat_id == t.cat_id and x.amount < 0
    )
    if spent > budget.limit:
        message = f"Budget exceeded for {t.cat_id}: {spent} / {budget.limit} KZT"
        return add_notification(state, message)
    return state


def on_budget_alert(event: Event, state: dict) -> dict:
    # BUDGET_ALERT handler: turn the event into a notification.
    return add_notification(state, event.payload["message"])


def on_balance_alert(event: Event, state: dict) -> dict:
    # BALANCE_ALERT handler: turn the event into a notification.
    return add_notification(state, event.payload["message"])
