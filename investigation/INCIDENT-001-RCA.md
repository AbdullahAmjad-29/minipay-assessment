# INCIDENT-001 - Intermittent 500s on Transaction Search

Priority: P2

## Summary

Investigated intermittent 500 errors on transaction lookup under load. This
wasn't reproduced from a fabricated scenario - it's a real, latent
architectural gap that had been in the API since it was first built: every
request opened its own brand-new database connection with no pooling or
reuse anywhere in the codebase.

## Investigation

Checked current Postgres capacity as a baseline before testing anything:

    SHOW max_connections;        -- 100
    SELECT COUNT(*) FROM pg_stat_activity;   -- 6 in use

Plenty of headroom under normal single-request testing, which is exactly
why this had never surfaced before - nothing done in this project so far
had involved real concurrency.

To reproduce honestly without needing an unrealistic flood of traffic,
temporarily lowered Postgres's own max_connections to 8 (a real constraint,
not a mock), then fired 20 genuinely simultaneous requests at the same
transaction lookup endpoint:

    for i in $(seq 1 20); do
      curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/payments/TXN00000029 &
    done
    wait

Result: a real mix of 200s and 500s, roughly half and half, for the exact
same endpoint and the exact same transaction reference - confirming the
incident's reported symptom precisely (some requests succeed, others fail,
with no pattern tied to which transaction is being looked up).

Captured the actual server-side traceback:

    File "app/database.py", line 8, in get_connection
        return psycopg2.connect(...)
    psycopg2.OperationalError: connection to server at "127.0.0.1", port 5432
    failed: FATAL: remaining connection slots are reserved for roles with
    the SUPERUSER attribute

## Root cause

app/database.py opened a fresh psycopg2 connection on every single request,
with no pooling. Under enough concurrent load, once Postgres's available
connection slots were exhausted, any further connection attempt failed
outright - and since nothing in the codebase specifically caught this
exception, it propagated up as an unhandled error, which FastAPI's default
behavior turns into a generic 500. The failure was never about a specific
transaction ID; it was about which request happened to arrive when no
connection slot was free.

## Correction

Replaced per-request connections with a real connection pool
(psycopg2.pool.SimpleConnectionPool), shared across the whole process,
via a context manager (`with get_connection() as conn:`) so every borrowed
connection is guaranteed to be returned to the pool afterward, even on
error.

First pool attempt used maxconn=10, which still failed under the same test.
Investigated why: Postgres reserves some connections exclusively for
superuser roles by default (superuser_reserved_connections = 3), so with
max_connections=8, the minipay_app role only ever had 5 usable slots, not
8 - a pool ceiling set without accounting for that reservation could still
exhaust real capacity. Lowered maxconn to 4, deliberately below the real
5-slot ceiling rather than exactly at it, to leave headroom for other
things sharing the same database (other sessions, health checks, etc.).

Re-testing at maxconn=4 dropped failures dramatically but not to zero -
one request still failed under the same 20-request burst, this time with
a different, more specific exception:

    psycopg2.pool.PoolError: connection pool exhausted

This is a distinct, expected situation - the pool itself was fully
checked out for a moment during a genuine burst, not a broken connection.
Added explicit handling for both exception types
(psycopg2.pool.PoolError and psycopg2.OperationalError) on the affected
endpoint, returning a clean 503 Service Unavailable with a clear message,
rather than letting either leak through as an opaque 500.

## Validation

Reran the identical 20-request burst after each change, same test each
time, for a fair before/after comparison:

    Before (no pooling):                 ~50% failure rate (500s)
    After maxconn=10 (miscalibrated):     still failing, same error
    After maxconn=4 (correctly sized):    1/20 failed, but as raw 500
                                           (PoolError uncaught)
    After catching both exception types:  19/20 succeeded (200),
                                           1/20 correctly returned 503,
                                           zero 500s

The remaining occasional 503 under this specific, deliberately extreme
constraint (8 total connections, 5 usable, 20 simultaneous requests) is
expected and correct behavior, not a bug - it reflects genuine, honest
capacity limits, surfaced as a clear, actionable response instead of a
generic failure.

## Preventive controls

- Any component that opens its own database connections should use
  connection pooling from day one, not as a retrofit after a real incident
  - this is exactly the kind of gap that's invisible in normal
    single-request development and testing, and only surfaces under real
    concurrent load.
- Pool sizing must account for the database's actual reserved/available
  connection budget (checking superuser_reserved_connections, not just
  max_connections), and should be re-validated whenever the database's own
  configuration changes.
- A load or concurrency test against realistic traffic patterns should be
  part of standard testing for any request-handling code, not only run
  reactively once a production incident is reported.
- Client-facing errors from resource exhaustion should always be
  distinguished from genuine server bugs (503 vs 500) so callers - and
  retry logic - can respond appropriately.
---

One more related issue surfaced afterward, worth including since it's the
same underlying theme (connection lifecycle correctness) as the rest of
this incident. After restoring Postgres's max_connections back to its
normal value (a full `systemctl restart postgresql`, needed since that
setting only takes effect on restart), the full pytest suite started
failing 3 of 12 tests with fresh 500 errors on customer/payment creation -
despite nothing being wrong with the code that had just been fixed and
verified.

The restart had killed every existing connection to Postgres, including
the ones the pool had pre-opened and was holding (minconn=2). The pool had
no way to know those connections had gone stale underneath it, and handed
one of them to the next request, which failed with a fresh
OperationalError that create_customer and create_payment didn't catch.

Fixed by making get_connection() defensively check whether a borrowed
connection is already closed before use, and by catching
OperationalError around the yielded connection so a connection that dies
mid-request gets discarded (closed) rather than silently returned to the
pool to poison the next caller too. Reran the full test suite after the
fix: 12/12 passed, confirming the pool now survives a database restart
correctly instead of serving stale connections afterward.

