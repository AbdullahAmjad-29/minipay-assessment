-- Average and p95 processing time (created_at to completed_at), where completed_at is set
SELECT
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))), 2) AS avg_seconds,
    ROUND(
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)))::numeric,
        2
    ) AS p95_seconds
FROM transactions
WHERE completed_at IS NOT NULL;
