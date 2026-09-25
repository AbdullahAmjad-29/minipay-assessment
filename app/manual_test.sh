#!/bin/bash
set -e
BASE="http://127.0.0.1:8000"

echo "== health =="
curl -s -i "$BASE/health"; echo -e "\n"

echo "== create customer (should be 201) =="
curl -s -i -X POST "$BASE/api/customers" -H "Content-Type: application/json" \
  -d '{"customer_ref": "TESTCUST001", "name": "Test User"}'; echo -e "\n"

echo "== duplicate customer (should be 409) =="
curl -s -i -X POST "$BASE/api/customers" -H "Content-Type: application/json" \
  -d '{"customer_ref": "TESTCUST001", "name": "Test User"}'; echo -e "\n"

echo "== create payment (should be 201) =="
PAYMENT=$(curl -s -X POST "$BASE/api/payments" -H "Content-Type: application/json" \
  -d '{"customer_id": 1001, "amount": 250.00}')
echo "$PAYMENT"
TXN=$(echo "$PAYMENT" | python3 -c "import json,sys;print(json.load(sys.stdin)['transaction_ref'])")
echo -e "\n"

echo "== get payment by ref (should be 200) =="
curl -s -i "$BASE/api/payments/$TXN"; echo -e "\n"

echo "== get customer payments (should be 200, list) =="
curl -s -i "$BASE/api/customers/1001/payments"; echo -e "\n"
