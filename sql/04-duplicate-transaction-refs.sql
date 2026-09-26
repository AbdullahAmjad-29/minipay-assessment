-- Duplicate transaction references (should normally return zero rows)
SELECT
    transaction_ref,
    COUNT(*) AS occurrence_count
FROM transactions
GROUP BY transaction_ref
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC;
