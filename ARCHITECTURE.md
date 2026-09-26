# MiniPay — Architecture

## Overview
MiniPay is a minimal payment-processing API + UI built for this assessment.
Stack: FastAPI (Python) + PostgreSQL, deployed later to Kubernetes.

## Database
PostgreSQL, schema from `database/schema.sql` (as provided), plus one
deliberate extension:

- `database/migrations/001_add_idempotency_key.sql` adds a nullable,
  uniquely-indexed `idempotency_key` column to `transactions`. The original
  schema had no way to safely handle a retried/duplicate payment submission
  (e.g. a client retrying after a network timeout, unsure if the first
  request succeeded). This is standard practice in real payment APIs
  (e.g. Stripe's Idempotency-Key header) and was added, not assumed present.

Access uses a dedicated least-privilege role (`minipay_app`), not the
Postgres superuser — the app can only touch what it needs.

## API design
- `POST /api/customers` — creates a customer; 409 on duplicate `customer_ref`
  (unique constraint), 422 on missing/invalid fields (via Pydantic).
- `POST /api/payments` — creates a transaction in `PROCESSING` status.
  Accepts an optional `Idempotency-Key` header; a repeated key returns the
  original transaction instead of creating a duplicate. 404 for an unknown
  customer, 422 for a non-positive amount.
- `GET /api/payments/{transaction_ref}` — looked up by the external
  transaction reference, not the internal DB id (avoids exposing raw
  primary keys externally).
- `GET /api/customers/{customer_id}/payments` — a customer's transaction
  history, newest first.
- `GET /health` — checks real DB connectivity (`SELECT 1`), not a hardcoded
  200; used later by Kubernetes readiness/liveness probes.

## Design decisions
- FastAPI over Flask: built-in request validation (Pydantic) gives clean
  422s on bad input with minimal code.
- `transaction_ref` is a random UUID-derived string, not sequential —
  sequential refs leak volume information in a payments context.
- Every DB-touching endpoint explicitly rolls back on error before
  returning, so a failed request never leaves the connection in a broken
  transaction state for the next query.
## Kubernetes

Deployed to a local Minikube cluster (Docker driver). Minikube is fully self-contained here instead.

Postgres runs as a StatefulSet, not a Deployment, backed by a PVC - a
database needs a stable identity and storage that survives pod restarts,
which a Deployment's interchangeable-pod model doesn't guarantee. The API
is a plain Deployment, since it's stateless and fine to restart or scale
freely.

Two real bugs surfaced and got fixed during this build, both documented in
detail in investigation/docker-postgres-connectivity.md:

- Postgres's own liveness probe killed it mid-bulk-load, because the default
  1 second probe timeout wasn't enough while it was legitimately busy.
  Fixed by widening timeoutSeconds and failureThreshold.
- The API had no dependency on Postgres being ready before it started, so
  it occasionally lost the startup race and got killed by its own liveness
  probe. Fixed with an init container that blocks on pg_isready until
  Postgres actually accepts connections.

The cluster-internal Postgres was seeded with a small manual dataset rather
than the full 50k-row set used for local SQL work, since
requirements/03-kubernetes-rancher.md doesn't call for any specific data
volume in the cluster, and this was already the second unplanned detour
into bulk-load mechanics rather than the deployment itself.
