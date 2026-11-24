# Tests for the web API. They check the same numbers the core tests check.

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_overview_numbers():
    d = client.get("/api/overview").json()
    assert d["income"] == 1895000
    assert d["expenses"] == 1538490
    assert d["total_balance"] == 651510


def test_final_report_flags_cafe_and_cash_forecast():
    d = client.get("/api/reports/final").json()
    assert d["exceeded_budgets"] == ["cafe"]
    assert d["balance_forecast"]["acc3"] == 1948


def test_event_bus_low_balance_alert():
    client.post("/api/frp/reset")
    body = {"name": "TRANSACTION_ADDED", "account_id": "acc3", "amount": -20000}
    state = client.post("/api/frp/publish", json=body).json()
    assert any("Low balance" in n for n in state["notifications"])
    client.post("/api/frp/reset")


def test_unknown_category_is_404():
    assert client.get("/api/pipelines/hierarchy?root=nope").status_code == 404
