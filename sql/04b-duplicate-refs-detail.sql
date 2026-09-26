-- Detail view of one duplicate pair, to understand the actual collision
SELECT id, transaction_ref, customer_id, amount, status, created_at
FROM transactions
WHERE transaction_ref = 'TXN00004999'
ORDER BY id;
