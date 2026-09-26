-- Breakdown of the reconciliation gap: SUCCESS transactions with no matching successful callback
WITH latest_callback AS (
    SELECT DISTINCT ON (transaction_id)
        transaction_id,
        callback_status
    FROM callbacks
    ORDER BY transaction_id, attempt_no DESC
)
SELECT
    CASE
        WHEN lc.transaction_id IS NULL THEN 'no callback recorded at all'
        ELSE 'latest callback is FAILED'
    END AS gap_reason,
    COUNT(*) AS transaction_count,
    SUM(t.amount) AS total_value
FROM transactions t
LEFT JOIN latest_callback lc ON lc.transaction_id = t.id
WHERE t.status = 'SUCCESS'
  AND (lc.transaction_id IS NULL OR lc.callback_status != 'SUCCESS')
GROUP BY gap_reason;
