"""Core diagnostic logic for a single transaction.

Kept separate from the CLI layer so this logic can be unit tested with
fake data, without needing a real database connection.
"""
import logging

logger = logging.getLogger(__name__)


def fetch_transaction(cursor, transaction_ref):
    """Fetch a transaction with its customer, or None if not found."""
    cursor.execute(
        """
        SELECT t.id, t.transaction_ref, t.customer_id, t.amount, t.status,
               t.created_at, t.completed_at, t.failure_code,
               c.customer_ref, c.name
        FROM transactions t
        JOIN customers c ON c.id = t.customer_id
        WHERE t.transaction_ref = %s;
        """,
        (transaction_ref,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "transaction_ref": row[1],
        "customer_id": row[2],
        "amount": float(row[3]),
        "status": row[4],
        "created_at": row[5],
        "completed_at": row[6],
        "failure_code": row[7],
        "customer_ref": row[8],
        "customer_name": row[9],
    }


def fetch_callbacks(cursor, transaction_id):
    """Fetch all callback attempts for a transaction, ordered oldest first."""
    cursor.execute(
        """
        SELECT attempt_no, http_status, callback_status, attempted_at
        FROM callbacks
        WHERE transaction_id = %s
        ORDER BY attempt_no ASC;
        """,
        (transaction_id,),
    )
    return [
        {
            "attempt_no": r[0],
            "http_status": r[1],
            "callback_status": r[2],
            "attempted_at": r[3],
        }
        for r in cursor.fetchall()
    ]


def detect_anomalies(transaction, callbacks, now):
    """Pure function: given transaction + callback data, return a list of
    (anomaly_description, recommended_action) tuples. Takes `now` as a
    parameter rather than calling datetime.now() internally, so tests can
    supply a fixed time and get deterministic results.
    """
    findings = []

    if transaction["status"] == "PROCESSING":
        age = now - transaction["created_at"]
        if age.total_seconds() > 15 * 60:
            findings.append((
                f"Stuck in PROCESSING for {age} (threshold: 15 minutes).",
                "Check the payment processor/worker for this transaction; "
                "consider manual status reconciliation or reversal if the "
                "processor confirms no charge occurred.",
            ))

    if transaction["status"] == "SUCCESS":
        if not callbacks:
            findings.append((
                "Transaction succeeded but no callback attempt was ever recorded.",
                "Verify the downstream notification system received the "
                "success event; manually trigger a callback if not.",
            ))
        elif callbacks[-1]["callback_status"] != "SUCCESS":
            findings.append((
                f"Transaction succeeded, but the latest callback attempt "
                f"(#{callbacks[-1]['attempt_no']}) is {callbacks[-1]['callback_status']}.",
                "Downstream system may not know this payment succeeded. "
                "Retry the callback or notify the downstream system manually.",
            ))

    if transaction["status"] == "FAILED" and transaction["failure_code"]:
        findings.append((
            f"Transaction failed with code: {transaction['failure_code']}.",
            "Review failure_code against processor documentation; "
            "advise customer to retry if the failure is recoverable "
            "(e.g. insufficient funds), escalate if not.",
        ))

    if len(callbacks) > 1:
        findings.append((
            f"{len(callbacks)} callback attempts recorded (retried "
            f"{len(callbacks) - 1} time(s)).",
            "Informational - not necessarily an issue, but worth noting "
            "if retry volume is unusually high across many transactions.",
        ))

    return findings


def build_report(cursor, transaction_ref, now):
    """Fetch everything and assemble the full diagnostic report as a dict.
    Returns None if the transaction doesn't exist.
    """
    transaction = fetch_transaction(cursor, transaction_ref)
    if transaction is None:
        logger.warning("Transaction not found: %s", transaction_ref)
        return None

    callbacks = fetch_callbacks(cursor, transaction["id"])
    anomalies = detect_anomalies(transaction, callbacks, now)

    return {
        "transaction": transaction,
        "callbacks": callbacks,
        "anomalies": [a for a, _ in anomalies],
        "recommended_actions": [r for _, r in anomalies] or [
            "No anomalies detected; transaction appears healthy."
        ],
    }
def health_summary(cursor):
    """Cross-dependency health check: DB reachable (implied by getting this
    far) plus a summary of stuck/failed transactions - the bonus feature.
    """
    cursor.execute("SELECT 1;")
    db_ok = cursor.fetchone() == (1,)

    cursor.execute(
        """
        SELECT COUNT(*) FROM transactions
        WHERE status = 'PROCESSING' AND created_at < NOW() - INTERVAL '15 minutes';
        """
    )
    stuck_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'FAILED';")
    failed_count = cursor.fetchone()[0]

    return {
        "database_reachable": db_ok,
        "stuck_processing_count": stuck_count,
        "failed_count": failed_count,
    }
