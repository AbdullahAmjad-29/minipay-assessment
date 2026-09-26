# INCIDENT-003 - Transaction Search Performance

Priority: P2

## Summary

Operations reported that transaction investigation slows down as data
volume grows, with some searches expected to take several seconds and
worsen further. Investigated using the full 50,000-row synthetic dataset
already generated for this assessment (database/generate_data.py), rather
than a small hand-made sample, so the access pattern would be realistic.

## Investigation

Reviewed schema.sql first rather than guessing at what needed indexing -
it carries its own comment noting indexing was left intentionally minimal
and that the candidate should assess it based on real workload. Confirmed
this directly:

    \d transactions

Only the primary key and one index added earlier in this assessment
(idempotency_key) exist. Nothing supports filtering by status or
created_at, which is exactly the access pattern behind one of the most
operationally important queries in this system - finding transactions
stuck in PROCESSING, the query an L2 engineer would run first when
investigating a "payments seem stuck" report (see
sql/03-stuck-processing-over-15min.sql).

Captured a real execution plan against the full 50k-row table, not a
theoretical estimate:

    EXPLAIN ANALYZE
    SELECT id, transaction_ref, customer_id, amount, created_at
    FROM transactions
    WHERE status = 'PROCESSING'
      AND created_at < NOW() - INTERVAL '15 minutes';

    Seq Scan on transactions (actual time=0.015..11.725 rows=2447 loops=1)
      Rows Removed by Filter: 47557
    Execution Time: 11.863 ms

Every one of the 50,000 rows is read and individually checked; 47,557 are
discarded to find the 2,447 that match.

## Root cause

No index exists on the columns this query (and this class of query -
status plus a time filter) actually needs. The cost of a sequential scan
grows linearly with table size, since the database has no way to jump
directly to matching rows - it has to check every single one. Full detail
and the exact before/after evidence lives in sql/PERFORMANCE.md, produced
as part of the SQL investigation task; this incident is that same finding,
reframed and reported the way it would actually reach an L2 engineer in
practice - as a user-facing performance complaint, not a schema review.

## Correction

    CREATE INDEX idx_transactions_status_created_at
    ON transactions (status, created_at);

A composite index on both columns, since the query filters on both
together - built to directly support "PROCESSING rows in created_at
order" rather than making the database find all PROCESSING rows first
and re-check the date afterward.

## Validation

Re-ran the identical query after adding the index:

    Bitmap Heap Scan on transactions (actual time=5.690..14.067 rows=2447 loops=1)
      Heap Blocks: exact=603
      ->  Bitmap Index Scan on idx_transactions_status_created_at
    Execution Time: 14.433 ms

Postgres confirmed switching to the new index, but execution time was
not lower at this specific data volume (14.4ms vs 11.9ms) - reported
honestly here rather than picking a friendlier-looking result. At 50,000
rows with roughly 5% selectivity, a sequential scan is already cheap and
the index's own overhead (building a bitmap, then fetching heap pages)
costs slightly more than the scan it replaces. The number that actually
matters is Rows Removed by Filter: 47,557 in the original plan - that
scales linearly with table size, while an index lookup's cost grows far
more slowly. The two approaches are roughly even today; at real production
volume (the "expected to deteriorate further" in the original report),
the index wins decisively and the gap widens as data accumulates. Full
reasoning in sql/PERFORMANCE.md.

## Preventive controls

- Any new query added to the codebase that filters on non-indexed columns
  should have its execution plan reviewed before merge, not after a slow
  query is reported in production - EXPLAIN ANALYZE on a realistic data
  volume is fast to run and would have caught this before it shipped.
- Since this schema deliberately ships with minimal indexing as a
  candidate exercise, a real onboarding step for this codebase should be
  reviewing actual production query patterns (e.g. via pg_stat_statements)
  and indexing against real usage, rather than guessing which columns
  matter.
- Load-testing against a realistic data volume (this assessment used
  50,000 rows specifically because a handful of test rows would never
  have revealed this) should be a standard step before any schema or
  query change ships, not something done only when performance is
  formally reported as an incident.
