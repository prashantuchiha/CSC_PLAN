# ADR 002: SQLite polling, claims and leases

Status: Accepted for Phase 2.

Context: The personal application needs background work on an older laptop. Phase 1 already
stores durable jobs in SQLite and exposes a repository/unit-of-work boundary. A separate queue
server would increase memory and operational burden without a measured need.

Decision: Run one opt-in local worker process. It polls SQLite and sleeps between empty polls.
Claiming uses one conditional `UPDATE ... RETURNING` statement, ordered by priority and creation
time, so competing claim attempts cannot both own the same queued row. A claim writes worker ID,
unique token, lease expiry, start time, revision and incremented attempts. Completion requires
the current token and unexpired lease, followed by the existing optimistic revision update.
Handlers can renew a lease explicitly through their execution context. Recovery requeues an
expired claim with bounded backoff, or fails it when attempts are exhausted.

Retries are at least once, not exactly once. A crash between an outside side effect and the job
commit can cause a repeat. The fake provider has no side effects and is safe to repeat. Future
handlers must use stable request keys, deduplicate writes and, for email, rely on provider-level
idempotency or reconciliation. The job claim token only protects SQLite state.

Phase 1's generic manual RUNNING transition is retained with a `manual` lease for compatibility.
The Phase 2 migration requeues legacy RUNNING rows that had no lease; their attempt counts and
payloads remain. Worker-owned rows cannot be manually completed through the API or CLI.

Consequences: No Redis, Celery, RabbitMQ or broker daemon is needed. SQLite remains the sole
structured state store. The worker opens short transactions for claim/result/recovery and no
session during handler execution or idle waits. SQLite's single-writer behavior is acceptable
for one personal worker; throughput and contention should be measured before adding processes.
An unresponsive handler can outlive its lease if it does not heartbeat; its eventual completion
is rejected, but its external side effect may already have happened.
