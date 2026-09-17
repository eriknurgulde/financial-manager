# Tests for Lab 6. Run them with: pytest -q

from core.domain import Account, Budget, Event, Transaction
from core.frp import (
    BALANCE_ALERT,
    BUDGET_ALERT,
    TRANSACTION_ADDED,
    EventBus,
    apply_transaction,
    check_budget_after_transaction,
    on_balance_alert,
    on_budget_alert,
)

ACCOUNTS = (Account("a1", "Wallet", 10000, "KZT"),)
BUDGETS = (Budget("b1", "food", 1000, "month"),)


def make_state(transactions=()):
    return {
        "accounts": ACCOUNTS,
        "budgets": BUDGETS,
        "transactions": transactions,
        "notifications": (),
    }


def test_event_is_a_namedtuple_without_id():
    e = Event("TEST", "2026-09-17", {"x": 1})
    assert e.name == "TEST"
    assert e.ts == "2026-09-17"
    assert e.payload == {"x": 1}
    assert not hasattr(e, "id")


def test_bus_publish_calls_subscribed_handler():
    bus = EventBus(make_state())
    bus.subscribe(BALANCE_ALERT, on_balance_alert)
    bus.publish(BALANCE_ALERT, {"message": "low"})
    assert bus.state["notifications"] == ("low",)


def test_bus_ignores_unsubscribed_event():
    bus = EventBus(make_state())
    bus.publish(BUDGET_ALERT, {"message": "ignored"})
    assert bus.state["notifications"] == ()


def test_apply_transaction_updates_balance():
    t = Transaction("t1", "a1", "food", -500, "2026-09-17", "x")
    event = Event(TRANSACTION_ADDED, "2026-09-17", {"transaction": t})
    new_state = apply_transaction(event, make_state())
    assert new_state["accounts"][0].balance == 9500
    assert new_state["transactions"] == (t,)


def test_apply_transaction_does_not_mutate_old_state():
    t = Transaction("t1", "a1", "food", -500, "2026-09-17", "x")
    event = Event(TRANSACTION_ADDED, "2026-09-17", {"transaction": t})
    old_state = make_state()
    apply_transaction(event, old_state)
    assert old_state["accounts"][0].balance == 10000


def test_check_budget_after_transaction_flags_exceeded():
    t = Transaction("t1", "a1", "food", -1500, "2026-09-17", "x")
    event = Event(TRANSACTION_ADDED, "2026-09-17", {"transaction": t})
    state = check_budget_after_transaction(event, make_state((t,)))
    assert len(state["notifications"]) == 1
    assert "food" in state["notifications"][0]


def test_check_budget_after_transaction_ignores_under_budget():
    t = Transaction("t1", "a1", "food", -100, "2026-09-17", "x")
    event = Event(TRANSACTION_ADDED, "2026-09-17", {"transaction": t})
    state = check_budget_after_transaction(event, make_state((t,)))
    assert state["notifications"] == ()


def test_on_budget_alert_adds_notification():
    event = Event(BUDGET_ALERT, "2026-09-17", {"message": "over budget"})
    state = on_budget_alert(event, make_state())
    assert state["notifications"] == ("over budget",)


def test_bus_chains_two_handlers_on_same_event():
    bus = EventBus(make_state())
    bus.subscribe(TRANSACTION_ADDED, apply_transaction)
    bus.subscribe(TRANSACTION_ADDED, check_budget_after_transaction)
    t = Transaction("t1", "a1", "food", -1500, "2026-09-17", "x")
    bus.publish(TRANSACTION_ADDED, {"transaction": t})
    assert bus.state["accounts"][0].balance == 8500
    assert len(bus.state["notifications"]) == 1
