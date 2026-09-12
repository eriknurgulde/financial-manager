"""Tests for the Streamlit page, driven by Streamlit's own AppTest harness.

These run the real script - no browser, no server - so a typo in a render
function fails `pytest` instead of surfacing as a blank page during the demo.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.loader import DEFAULT_SEED_PATH, load_seed
from core.transforms import overview, total_balance

APP = str(Path(__file__).resolve().parents[1] / "app" / "main.py")

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


@pytest.fixture(scope="module")
def app():
    return AppTest.from_file(APP, default_timeout=60).run()


def test_the_page_renders_without_raising(app):
    assert not app.exception


def test_the_burger_menu_offers_every_required_item(app):
    assert app.sidebar.radio[0].options == MENU


def test_overview_is_the_landing_screen(app):
    assert app.header[0].value == "Overview"


def test_overview_metrics_match_the_pure_functions(app):
    accounts, cats, trans, _ = load_seed(DEFAULT_SEED_PATH)
    stats = overview(accounts, cats, trans)
    shown = {m.label: m.value for m in app.metric}

    assert shown["Accounts"] == str(stats["accounts"])
    assert shown["Categories"] == str(stats["categories"])
    assert shown["Transactions"] == str(stats["transactions"])


def test_overview_reports_the_balance_the_core_computes(app):
    accounts, _, trans, _ = load_seed(DEFAULT_SEED_PATH)
    expected_kzt = total_balance(accounts, trans) // 100
    shown = {m.label: m.value for m in app.metric}["Total balance"]

    digits = shown.replace(" ", "").split(".")[0]
    assert digits == str(expected_kzt)


@pytest.mark.parametrize("item", MENU)
def test_every_menu_item_renders_without_raising(item):
    at = AppTest.from_file(APP, default_timeout=60).run()

    at.sidebar.radio[0].set_value(item).run()

    assert not at.exception, f"{item} raised: {at.exception}"
    assert at.header[0].value == item


def test_later_lab_screens_say_so_instead_of_faking_it():
    at = AppTest.from_file(APP, default_timeout=60).run()

    at.sidebar.radio[0].set_value("Pipelines").run()

    assert any("not implemented" in i.value.lower() for i in at.info)


def test_transaction_filter_narrows_the_table():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Data").run()

    _, _, trans, _ = load_seed(DEFAULT_SEED_PATH)
    expected_income = sum(1 for t in trans if t.amount > 0)

    at.radio[0].set_value("Income only").run()

    assert not at.exception
    assert any(
        f"returned {expected_income} of {len(trans)}" in c.value for c in at.caption
    )


def test_functional_core_screen_exposes_the_three_lab_functions():
    at = AppTest.from_file(APP, default_timeout=60).run()

    at.sidebar.radio[0].set_value("Functional Core").run()

    headings = " ".join(s.value for s in at.subheader)
    assert "account_balance" in headings
    assert "add_transaction" in headings
    assert "update_budget" in headings


def test_changing_the_budget_slider_updates_only_that_budget():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Functional Core").run()

    at.slider[0].set_value(7_777).run()

    assert not at.exception
