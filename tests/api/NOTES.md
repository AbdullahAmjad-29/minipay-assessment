 API testing notes: timeouts, retries, idempotency, 4xx vs 5xx

Handling timeouts: a client talking to this API should set both a connect
timeout and a read timeout, not rely on the OS default (which is often no
timeout at all). If the server is unreachable, fail fast rather than hang
the caller indefinitely. The server side matters too - our own
get_connection() sets connect_timeout=5 on the database connection for
exactly this reason, learned directly while building this: without it, a
genuinely unreachable Postgres would hang every request rather than
failing quickly with a clear error.

Retries: safe to retry automatically only for requests that are actually
idempotent, or that failed before any state changed. A GET is always safe
to retry. A POST /api/payments is only safe to retry automatically if the
client supplies the same Idempotency-Key on every attempt - otherwise a
retry after a timeout (where the first attempt may have actually
succeeded server-side, just failed to respond in time) risks creating a
real duplicate payment. Retries should also back off (not retry instantly
in a tight loop) and should specifically distinguish 5xx/network failures,
worth retrying, from 4xx failures, which won't succeed no matter how many
times they're retried.

Idempotency: built directly into POST /api/payments via an optional
Idempotency-Key header - the same key submitted twice returns the
original transaction instead of creating a second one. This is the
correct mechanism for exactly the retry scenario above: a client that
isn't sure whether its first request landed can safely resend with the
same key and get back the real, single result either way.

4xx vs 5xx: a 4xx means the request itself was wrong in some way the
client can fix - bad input, an unknown resource, missing or invalid auth
- and retrying the identical request will never help. A 5xx means the
server (or something it depends on) failed to do its job even though the
request was valid, and retrying may genuinely succeed once the underlying
problem clears. This distinction isn't just theoretical here - it's
exactly what INCIDENT-001 was about. The original bug returned a generic
500 whenever the database's connection capacity was exhausted, which
technically wasn't wrong (it was a real server-side failure), but it gave
callers no way to tell "this will never work, stop retrying this exact
request" apart from "this is temporary, a moment later it'll probably
succeed." The fix specifically returns 503 for connection-pool exhaustion
instead of a bare 500, so a well-behaved client (or our own retry logic)
can treat it as the second case and retry with backoff, rather than
treating every 500 the same way.

## Running the suite

    python3 -m pytest tests/api/ -v

Requires the API running locally (or reachable via API_BASE_URL) and a
valid API_KEY set in the environment, matching the running instance's
configuration. API testing notes: timeouts, retries, idempotency, 4xx vs 5xx

Handling timeouts: a client talking to this API should set both a connect
timeout and a read timeout, not rely on the OS default (which is often no
timeout at all). If the server is unreachable, fail fast rather than hang
the caller indefinitely. The server side matters too - our own
get_connection() sets connect_timeout=5 on the database connection for
exactly this reason, learned directly while building this: without it, a
genuinely unreachable Postgres would hang every request rather than
failing quickly with a clear error.

Retries: safe to retry automatically only for requests that are actually
idempotent, or that failed before any state changed. A GET is always safe
to retry. A POST /api/payments is only safe to retry automatically if the
client supplies the same Idempotency-Key on every attempt - otherwise a
retry after a timeout (where the first attempt may have actually
succeeded server-side, just failed to respond in time) risks creating a
real duplicate payment. Retries should also back off (not retry instantly
in a tight loop) and should specifically distinguish 5xx/network failures,
worth retrying, from 4xx failures, which won't succeed no matter how many
times they're retried.

Idempotency: built directly into POST /api/payments via an optional
Idempotency-Key header - the same key submitted twice returns the
original transaction instead of creating a second one. This is the
correct mechanism for exactly the retry scenario above: a client that
isn't sure whether its first request landed can safely resend with the
same key and get back the real, single result either way.

4xx vs 5xx: a 4xx means the request itself was wrong in some way the
client can fix - bad input, an unknown resource, missing or invalid auth
- and retrying the identical request will never help. A 5xx means the
server (or something it depends on) failed to do its job even though the
request was valid, and retrying may genuinely succeed once the underlying
problem clears. This distinction isn't just theoretical here - it's
exactly what INCIDENT-001 was about. The original bug returned a generic
500 whenever the database's connection capacity was exhausted, which
technically wasn't wrong (it was a real server-side failure), but it gave
callers no way to tell "this will never work, stop retrying this exact
request" apart from "this is temporary, a moment later it'll probably
succeed." The fix specifically returns 503 for connection-pool exhaustion
instead of a bare 500, so a well-behaved client (or our own retry logic)
can treat it as the second case and retry with backoff, rather than
treating every 500 the same way.

## Running the suite

    python3 -m pytest tests/api/ -v

Requires the API running locally (or reachable via API_BASE_URL) and a
valid API_KEY set in the environment, matching the running instance's
configuration.
