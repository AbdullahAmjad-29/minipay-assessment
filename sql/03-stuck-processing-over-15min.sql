-- Transactions stuck in PROCESSING for more than 15 minutes
SELECT
    id,
    transaction_ref,
    customer_id,
    amount,
    created_at,
    NOW() - created_at AS time_stuck
FROM transactions
WHERE status = 'PROCESSING'
  AND created_at < NOW() - INTERVAL '15 minutes'
ORDER BY created_at ASC;
