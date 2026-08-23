from fastapi.testclient import TestClient
from backend.app import app

client=TestClient(app)

def test_health():
    r=client.get("/health")
    assert r.status_code==200
    assert r.json()["status"]=="ok"

def test_context_high_risk():
    payload={"amount":48500,"hour":3,"customer_avg_amount":1850,"transactions_24h":7,
             "account_age_days":18,"new_device":True,"new_location":True}
    r=client.post("/predict/context",json=payload)
    assert r.status_code==200
    data=r.json()
    assert data["risk_level"]=="HIGH"
    assert data["decision"]=="BLOCK"
    assert data["risk_score"]>=75

def test_investigations():
    r=client.get("/investigations")
    assert r.status_code==200
    assert isinstance(r.json(),list)
