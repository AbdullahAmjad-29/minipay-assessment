-- Top 10 customers by successful transaction value
SELECT
    c.id AS customer_id,
    c.customer_ref,
    c.name,
    COUNT(t.id) AS successful_transactions,
    SUM(t.amount) AS total_successful_value
FROM customers c
JOIN transactions t ON t.customer_id = c.id
WHERE t.status = 'SUCCESS'
GROUP BY c.id, c.customer_ref, c.name
ORDER BY total_successful_value DESC
LIMIT 10;
