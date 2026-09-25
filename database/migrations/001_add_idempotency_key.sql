-- Adds idempotency support to transactions.
-- Rationale: the original schema had no mechanism to safely handle
-- duplicate/retried payment submissions (e.g. a client retrying after
-- a timeout, unsure if the first request succeeded). A nullable,
-- uniquely-indexed idempotency_key lets POST /api/payments detect and
-- return the original transaction instead of creating a duplicate one.
ALTER TABLE transactions ADD COLUMN idempotency_key VARCHAR(64) NULL;
CREATE UNIQUE INDEX idx_transactions_idempotency_key
  ON transactions (idempotency_key)
  WHERE idempotency_key IS NOT NULL;
