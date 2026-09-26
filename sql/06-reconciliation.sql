-- Reconciliation: transaction-table SUCCESS vs callback-table SUCCESS (latest attempt per transaction)
WITH latest_callback AS (
    SELECT DISTINCT ON (transaction_id)
        transaction_id,
        callback_status
    FROM callbacks
    ORDER BY transaction_id, attempt_no DESC
)
SELECT
    (SELECT COUNT(*) FROM transactions WHERE status = 'SUCCESS') AS tx_success_count,
    (SELECT SUM(amount) FROM transactions WHERE status = 'SUCCESS') AS tx_success_value,
    (SELECT COUNT(*)
       FROM transactions t
       JOIN latest_callback lc ON lc.transaction_id = t.id
      WHERE lc.callback_status = 'SUCCESS') AS callback_success_count,
    (SELECT SUM(t.amount)
       FROM transactions t
       JOIN latest_callback lc ON lc.transaction_id = t.id
      WHERE lc.callback_status = 'SUCCESS') AS callback_success_value;
