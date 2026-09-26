#!/usr/bin/env python3
"""L2 support diagnostic tool for MiniPay transactions.

Usage:
    python support_tool.py --transaction TXN000123
    python support_tool.py --transaction TXN000123 --json
    python support_tool.py --health
    python support_tool.py --health --json
"""
import argparse
import json
import logging
import sys
from datetime import datetime

from db import get_connection
from diagnostics import build_report, health_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_CONNECTION_ERROR = 2


def print_human_report(report):
    t = report["transaction"]
    print(f"Transaction: {t['transaction_ref']}")
    print(f"Customer:    {t['customer_ref']} ({t['customer_name']})")
    print(f"Amount:      {t['amount']}")
    print(f"Status:      {t['status']}")
    print(f"Created:     {t['created_at']}")
    print(f"Completed:   {t['completed_at'] or '(not completed)'}")
    if t["failure_code"]:
        print(f"Failure code: {t['failure_code']}")

    print(f"\nCallback attempts: {len(report['callbacks'])}")
    for cb in report["callbacks"]:
        print(f"  attempt {cb['attempt_no']}: {cb['callback_status']} "
              f"(http {cb['http_status']}) at {cb['attempted_at']}")

    print("\nAnomalies:")
    for a in report["anomalies"]:
        print(f"  - {a}")

    print("\nRecommended action(s):")
    for r in report["recommended_actions"]:
        print(f"  - {r}")


def print_human_health(summary):
    print(f"Database reachable: {summary['database_reachable']}")
    print(f"Transactions stuck in PROCESSING (>15min): {summary['stuck_processing_count']}")
    print(f"Total FAILED transactions: {summary['failed_count']}")


def main():
    parser = argparse.ArgumentParser(description="MiniPay L2 support diagnostic tool")
    parser.add_argument("--transaction", help="Transaction reference, e.g. TXN00000123")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON instead of a human report")
    parser.add_argument("--health", action="store_true", help="Run a health check across DB dependencies and summarize stuck/failed transactions")
    args = parser.parse_args()

    if not args.health and not args.transaction:
        parser.error("--transaction is required unless --health is used")

    try:
        conn = get_connection()
    except Exception as e:
        logger.error("Could not connect to database: %s", e)
        print(f"ERROR: could not connect to database: {e}", file=sys.stderr)
        sys.exit(EXIT_CONNECTION_ERROR)

    try:
        cur = conn.cursor()

        if args.health:
            summary = health_summary(cur)
            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                print_human_health(summary)
            sys.exit(EXIT_OK)

        report = build_report(cur, args.transaction, datetime.now())
    finally:
        conn.close()

    if report is None:
        if args.json:
            print(json.dumps({"error": "transaction_not_found", "transaction_ref": args.transaction}))
        else:
            print(f"No transaction found with reference: {args.transaction}", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_human_report(report)

    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
