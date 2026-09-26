# Query performance investigation

Targeted query: sql/03-stuck-processing-over-15min.sql (transactions stuck in
PROCESSING for more than 15 minutes). Picked this one deliberately - it's the
query an L2 engineer would actually run first during a real "payments seem
stuck" incident, so its performance matters more than most of the others.

## Before

schema.sql ships with a comment noting indexing was left intentionally
minimal. Confirmed that directly:

    \d transactions

Only the primary key and the idempotency_key index (added earlier in this
project) exist. Nothing on status or created_at, which is exactly what this
query filters on.

    EXPLAIN ANALYZE
    SELECT id, transaction_ref, customer_id, amount, created_at
    FROM transactions
    WHERE status = 'PROCESSING'
      AND created_at < NOW() - INTERVAL '15 minutes';

    Seq Scan on transactions (actual time=0.015..11.725 rows=2447 loops=1)
      Filter: (status = 'PROCESSING' AND created_at < now() - interval)
      Rows Removed by Filter: 47557
    Execution Time: 11.863 ms

Postgres reads all 50,000 rows and discards 47,557 of them to find the 2,447
that match. At this table size that's 11.9ms - fast in absolute terms, but
the cost here scales linearly with table size, since every row has to be
individually checked regardless of how many actually match.

## Change made

    CREATE INDEX idx_transactions_status_created_at
    ON transactions (status, created_at);

A composite index on both columns together, rather than a single-column
index on just status, since the query filters on both at once - the index
itself can encode "PROCESSING rows in created_at order" as one structure.

## After

    Bitmap Heap Scan on transactions (actual time=5.690..14.067 rows=2447 loops=1)
      Recheck Cond: (status = 'PROCESSING' AND created_at < now() - interval)
      Heap Blocks: exact=603
      ->  Bitmap Index Scan on idx_transactions_status_created_at
            (actual time=2.872..2.873 rows=2447 loops=1)
    Execution Time: 14.433 ms

Postgres does switch to using the new index (confirmed by the plan itself),
but execution time is actually very slightly higher than before (14.4ms vs
11.9ms), not lower.

## Honest interpretation of that result

This isn't a failed fix - it's what indexing genuinely looks like at small
scale, and it's worth stating plainly rather than picking a rerun that looks
better. At 50,000 rows with about 5% selectivity (2,447 of 50,000 rows
match), a sequential scan is already cheap: one linear pass, likely mostly
served from cache. The index path has its own real overhead - building a
bitmap of matching row locations, then jumping around to fetch the actual
heap pages (Heap Blocks: exact=603) - and at this size that indirection
costs slightly more than the scan it replaces.

The number that actually matters for judging this fix isn't the millisecond
total, it's Rows Removed by Filter: 47,557 in the before plan. That number
grows linearly with table size - at 5 million rows the sequential scan
would need to read and discard roughly 4.75 million rows every time this
query runs, while the index-based lookup's cost grows far more slowly,
closer to logarithmically, as the table grows. The two approaches are
roughly a wash today; at real production scale the index wins decisively,
and the gap only widens as data accumulates.

This is also exactly why the schema's own comment said to assess indexing
based on workload rather than index every column by default - an index
isn't free. It has to be maintained on every INSERT and UPDATE that touches
transactions, so adding one that a workload doesn't actually need is a real
cost with no offsetting benefit. This one is justified by the query pattern
and by where the data volume is headed, not by what today's 50k-row
snapshot happens to measure.
