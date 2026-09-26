"""Unit tests for diagnostics.detect_anomalies - pure logic, no real DB.

Each test constructs fake transaction/callback dicts directly, matching
the shape build_report() produces, and passes a fixed `now` so results
are deterministic regardless of when the test suite actually runs.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from diagnostics import detect_anomalies

FIXED_NOW = datetime(2026, 9, 26, 12, 0, 0)


def make_transaction(**overrides):
    base = {
        "id": 1,
        "transaction_ref": "TXN00000001",
        "customer_id": 1,
        "amount": 100.0,
        "status": "SUCCESS",
        "created_at": FIXED_NOW - timedelta(minutes=5),
        "completed_at": FIXED_NOW - timedelta(minutes=4),
        "failure_code": None,
        "customer_ref": "CUST000001",
        "customer_name": "Test Customer",
    }
    base.update(overrides)
    return base


def test_processing_under_threshold_is_not_flagged():
    tx = make_transaction(status="PROCESSING", created_at=FIXED_NOW - timedelta(minutes=5))
    findings = detect_anomalies(tx, [], FIXED_NOW)
    assert findings == []


def test_processing_over_threshold_is_flagged():
    tx = make_transaction(status="PROCESSING", created_at=FIXED_NOW - timedelta(minutes=20))
    findings = detect_anomalies(tx, [], FIXED_NOW)
    assert len(findings) == 1
    assert "Stuck in PROCESSING" in findings[0][0]


def test_success_with_no_callback_is_flagged():
    tx = make_transaction(status="SUCCESS")
    findings = detect_anomalies(tx, [], FIXED_NOW)
    assert any("no callback attempt" in f[0] for f in findings)


def test_success_with_successful_callback_is_healthy():
    tx = make_transaction(status="SUCCESS")
    callbacks = [{"attempt_no": 1, "http_status": 200, "callback_status": "SUCCESS", "attempted_at": FIXED_NOW}]
    findings = detect_anomalies(tx, callbacks, FIXED_NOW)
    assert findings == []


def test_success_with_failed_latest_callback_is_flagged():
    tx = make_transaction(status="SUCCESS")
    callbacks = [
        {"attempt_no": 1, "http_status": 500, "callback_status": "FAILED", "attempted_at": FIXED_NOW},
    ]
    findings = detect_anomalies(tx, callbacks, FIXED_NOW)
    assert any("latest callback attempt" in f[0] for f in findings)


def test_success_recovers_after_failed_then_successful_retry():
    """A FAILED attempt followed by a later SUCCESS attempt should NOT be
    flagged - this is the exact distinction query 6's reconciliation
    logic depends on (latest attempt wins, not just any attempt).
    """
    tx = make_transaction(status="SUCCESS")
    callbacks = [
        {"attempt_no": 1, "http_status": 500, "callback_status": "FAILED", "attempted_at": FIXED_NOW - timedelta(minutes=2)},
        {"attempt_no": 2, "http_status": 200, "callback_status": "SUCCESS", "attempted_at": FIXED_NOW - timedelta(minutes=1)},
    ]
    findings = detect_anomalies(tx, callbacks, FIXED_NOW)
    # The reconciliation check itself should find nothing wrong - but the
    # separate multi-attempt note still fires, since 2 attempts were made.
    # This is correct, informational behavior, not a reconciliation problem.
    assert not any("latest callback attempt" in f[0] for f in findings)
    assert not any("no callback attempt" in f[0] for f in findings)


def test_failed_transaction_with_failure_code_is_flagged():
    tx = make_transaction(status="FAILED", failure_code="INSUFFICIENT_FUNDS")
    findings = detect_anomalies(tx, [], FIXED_NOW)
    assert any("INSUFFICIENT_FUNDS" in f[0] for f in findings)


def test_multiple_callback_attempts_noted():
    tx = make_transaction(status="SUCCESS")
    callbacks = [
        {"attempt_no": 1, "http_status": 500, "callback_status": "FAILED", "attempted_at": FIXED_NOW - timedelta(minutes=2)},
        {"attempt_no": 2, "http_status": 200, "callback_status": "SUCCESS", "attempted_at": FIXED_NOW - timedelta(minutes=1)},
    ]
    findings = detect_anomalies(tx, callbacks, FIXED_NOW)
    assert any("2 callback attempts recorded" in f[0] for f in findings)
