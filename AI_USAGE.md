
Tool used: Claude (Anthropic), via claude.ai chat.

Where it was used
- Designing the API surface (endpoints, request/response shapes) against
  the given database schema before writing code.
- Writing the FastAPI app (`app/main.py`, `app/database.py`) and the
  Postgres/CentOS environment setup.
- Diagnosing real issues hit during development

Representative interactions
1. Asked it to design the API surface for the 5 required endpoints against
   `database/schema.sql`, including how to handle duplicate submissions.
2. Asked for help resolving a `pg_hba.conf` lockout caused by setting
   local auth to `md5` for all roles including `postgres`, which has no
   password set by default on a fresh CentOS install.
3. Asked it to diagnose a 500 error on `POST /api/payments` — traced to an
   `idempotency_key` column that did not actually exist in the provided
   schema.
4. Asked it to diagnose why the Postgres pod restarted mid-bulk-data-load;
   traced to default liveness/readiness probe timeouts (1s) being too
   short under heavy write load, not a memory or storage issue as
   initially suspected.
5. Asked it to explain why the API pod restarted once on its first
   rollout; walked through the actual pod events together to distinguish
   a "connection refused" phase (app not started yet) from a "timeout"
   phase (app up, but blocked on an unready dependency), which pointed at
   a missing startup-ordering guarantee between the Deployment and the
   StatefulSet, not a probe-timeout issue like the Postgres one.

Validation
Every generated behavior was manually verified with real curl requests
against the running API and a real database, not assumed correct from
reading the code — see `app/manual_test.sh`. Status codes, response
bodies, and duplicate-detection behavior were all checked against actual
HTTP responses, not just inspected.
Every Kubernetes fix was verified against actual kubectl output before being
considered done - restart counts, pod events, and rollout status - not
assumed correct because the YAML applied without error.


Example of catching and correcting AI-generated output
Claude's first version of `POST /api/payments` referenced an
`idempotency_key` column and inserted without a `created_at` value,
assuming a design that didn't match the actual provided schema (no such
column exists, and `created_at` has no database default on `transactions`,
unlike on `customers`). Running it produced a real `500 Internal Server
Error`. Rather than accepting a quick patch, we diagnosed the root cause
against the real schema.sql, then deliberately added a migration
(`database/migrations/001_add_idempotency_key.sql`) to extend the schema
properly, with the reasoning documented in ARCHITECTURE.md, instead of
silently dropping the idempotency feature.

