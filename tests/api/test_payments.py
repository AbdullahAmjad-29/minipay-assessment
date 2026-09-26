import time
import uuid
import requests


def _make_customer(base_url, auth_headers):
    ref = f"TEST{uuid.uuid4().hex[:8].upper()}"
    resp = requests.post(
        f"{base_url}/api/customers",
        headers=auth_headers,
        json={"customer_ref": ref, "name": "Payment Test Customer"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_payment_success(base_url, auth_headers):
    customer_id = _make_customer(base_url, auth_headers)
    resp = requests.post(
        f"{base_url}/api/payments",
        headers=auth_headers,
        json={"customer_id": customer_id, "amount": 50.00},
    )
    assert resp.status_code == 201
    body = resp.json()
    # response schema/content assertions
    for field in ("id", "transaction_ref", "customer_id", "amount", "status", "created_at"):
        assert field in body
    assert body["status"] == "PROCESSING"
    assert body["transaction_ref"].startswith("TXN")


def test_create_payment_invalid_amount(base_url, auth_headers):
    customer_id = _make_customer(base_url, auth_headers)
    resp = requests.post(
        f"{base_url}/api/payments",
        headers=auth_headers,
        json={"customer_id": customer_id, "amount": -5},
    )
    assert resp.status_code == 422


def test_create_payment_unknown_customer(base_url, auth_headers):
    resp = requests.post(
        f"{base_url}/api/payments",
        headers=auth_headers,
        json={"customer_id": 999999999, "amount": 10.00},
    )
    assert resp.status_code == 404


def test_create_payment_idempotent_duplicate(base_url, auth_headers):
    customer_id = _make_customer(base_url, auth_headers)
    key = str(uuid.uuid4())
    headers = {**auth_headers, "Idempotency-Key": key}
    payload = {"customer_id": customer_id, "amount": 77.00}

    first = requests.post(f"{base_url}/api/payments", headers=headers, json=payload)
    second = requests.post(f"{base_url}/api/payments", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    # same transaction returned both times, not two separate ones
    assert first.json()["transaction_ref"] == second.json()["transaction_ref"]
    assert first.json()["id"] == second.json()["id"]


def test_get_payment_unknown_ref_returns_404(base_url):
    resp = requests.get(f"{base_url}/api/payments/TXNDOESNOTEXIST00")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_get_payment_response_time(base_url, auth_headers):
    """Basic response-time assertion - a health/lookup endpoint should
    respond quickly under normal conditions. Threshold is deliberately
    generous (2s) since this hits a real database, not a mock.
    """
    customer_id = _make_customer(base_url, auth_headers)
    created = requests.post(
        f"{base_url}/api/payments",
        headers=auth_headers,
        json={"customer_id": customer_id, "amount": 15.00},
    ).json()

    start = time.monotonic()
    resp = requests.get(f"{base_url}/api/payments/{created['transaction_ref']}")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 2.0, f"response took {elapsed:.2f}s, expected under 2s"


def test_get_customer_payments_list(base_url, auth_headers):
    customer_id = _make_customer(base_url, auth_headers)
    requests.post(
        f"{base_url}/api/payments",
        headers=auth_headers,
        json={"customer_id": customer_id, "amount": 22.00},
    )
    resp = requests.get(f"{base_url}/api/customers/{customer_id}/payments")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["amount"] == 22.0
