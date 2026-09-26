-- Composite index supporting the "stuck in PROCESSING" query and similar status+time filters
CREATE INDEX idx_transactions_status_created_at
ON transactions (status, created_at);
