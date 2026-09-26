import time
import uuid
import requests


def test_create_customer_success(base_url, auth_headers):
    ref = f"TEST{uuid.uuid4().hex[:8].upper()}"
    resp = requests.post(
        f"{base_url}/api/customers",
        headers=auth_headers,
        json={"customer_ref": ref, "name": "Pytest Customer"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["customer_ref"] == ref
    assert body["name"] == "Pytest Customer"
    assert "id" in body
    assert "created_at" in body


def test_create_customer_missing_field(base_url, auth_headers):
    resp = requests.post(
        f"{base_url}/api/customers",
        headers=auth_headers,
        json={"name": "No Ref Provided"},
    )
    assert resp.status_code == 422


def test_create_customer_duplicate_ref(base_url, auth_headers):
    ref = f"TEST{uuid.uuid4().hex[:8].upper()}"
    payload = {"customer_ref": ref, "name": "Dup Test"}
    first = requests.post(f"{base_url}/api/customers", headers=auth_headers, json=payload)
    assert first.status_code == 201

    second = requests.post(f"{base_url}/api/customers", headers=auth_headers, json=payload)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_create_customer_no_api_key(base_url, no_auth_headers):
    resp = requests.post(
        f"{base_url}/api/customers",
        headers=no_auth_headers,
        json={"customer_ref": f"TEST{uuid.uuid4().hex[:8]}", "name": "Should Fail"},
    )
    assert resp.status_code == 401


def test_create_customer_wrong_api_key(base_url):
    resp = requests.post(
        f"{base_url}/api/customers",
        headers={"X-API-Key": "wrong-key", "Content-Type": "application/json"},
        json={"customer_ref": f"TEST{uuid.uuid4().hex[:8]}", "name": "Should Fail"},
    )
    assert resp.status_code == 401
