# Architecture overview

China Masters Research OS is a modular monolith. One Python package contains independently
replaceable domain, application, infrastructure, and interface layers. SQLite holds structured
state, and the local filesystem holds human-readable artifacts. Phase 2 adds a separate opt-in
worker process for job execution. Phase 3 adds transactional research intake, context queries,
and an independently launched stdio MCP adapter.

## Call flow and dependency direction

```text
REST / CLI / MCP / future UI
       ↓
Application Services
       ↓
Domain
       ↓
Ports
       ↓
Infrastructure Adapters
```

This is a runtime interaction diagram, not a permission for the domain to import infrastructure.
Source dependencies point inward: domain imports only Python's standard library; application
imports domain and application contracts; infrastructure implements those contracts; interface
handlers call injected application services. `bootstrap.Container` wires the concrete adapters.
Architecture tests enforce those import boundaries. External integrations are absent.

Repositories are domain contracts; transaction, storage and provider contracts live in application
ports. The domain itself does not call application ports. Application command/query objects are
ordinary dataclasses. Pydantic request/response objects stay in the HTTP interface. SQLAlchemy
models never leave infrastructure; repositories copy values into domain dataclasses.

## Services and transactions

UniversityService and ProfessorService handle identity records and reference validation.
ResearchEvidenceService handles sources and provenance. WorkspaceService obtains known entities
and delegates folder creation to FileStorage. JobService creates, queries and controls jobs.
Phase 3 adds ProgramService, ProfessorContactService, PublicationService, StudyPlanService,
EmailRecordService and ContactAttemptService. ResearchIngestionService coordinates source,
contact, fact and publication repositories in one transaction. ResearchContextService returns
bounded professor/university views and freshness lists. The MCP server at `interfaces/mcp/`
calls these services through `bootstrap.Container`; it does not import SQLAlchemy or FileStorage
implementations.
JobExecutionService handles claims, completion, retries and recovery. JobWorker dispatches through
JobHandlerRegistry and does not access SQLAlchemy or FastAPI.
Each database operation opens a short-lived unit of work. Writes commit explicitly; on any exit,
uncommitted changes roll back and the session closes. No session is global or shared between
requests. The process-wide engine is a connection factory, not shared mutable domain state.

Batch creation validates all targets, inserts one job per target, and commits once. A failed
reference or insert leaves no partial batch. Explicit foreign keys protect concrete relations
even below the service boundary; ON DELETE RESTRICT preserves evidence/history. There are no
public deletion workflows yet. UUIDs avoid name-based identity and allow imports/merges later.
Canonical names are not unique: aliases and real-world duplicate names require explicit future
deduplication rules, not an unsafe blanket unique constraint.

ResearchFact and ResearchJob use polymorphic `(entity_type, entity_id)` references. SQL cannot
express their target as one foreign key without a shared entity registry. Application services
validate these references in the same unit of work. Direct SQL writes bypass that validation;
future deletes must preserve/check these references or introduce a registry. This is a deliberate
Phase 1 tradeoff, not a claim of database-enforced polymorphic referential integrity.

## Provenance

Every research fact stores a JSON value, source ID, field name, target, and verification status.
Multiple facts may coexist for the same field, including conflicting/outdated facts. No fact
automatically overwrites canonical entity metadata. All non-job domain entity types can be fact
targets. Basic identity entry need not pretend to be verified research.

Verified official facts require an official source category; publication verification requires
a publication source; secondary verification permits secondary or academic-index sources. The
service stamps a missing verification time for verified facts. This enforces metadata consistency,
not external truth. Future research handlers must submit candidate facts through this service
and a review policy. Verified contact methods require a source reference.

UTC-aware datetimes are used in the domain. Naive timestamps are rejected and timezone-aware
inputs are normalized to UTC. SQLite stores UTC wall times through a type adapter and restores
UTC tzinfo when reading. Decimal values represent tuition/duration; the database stores two
decimal places. JSON facts/payloads reject non-finite numbers, non-JSON types and non-string keys.

## Durable jobs

```text
QUEUED → RUNNING → COMPLETED
   │        ├──→ FAILED (attempts exhausted)
   │        ├──→ QUEUED (delayed bounded retry)
   │        └──→ WAITING_FOR_REVIEW → QUEUED (review resume)
   └──────────────────────────────→ CANCELLED
```

RUNNING, FAILED, and WAITING_FOR_REVIEW may also be cancelled. COMPLETED and CANCELLED are
terminal. Cancelling an already-cancelled job is idempotent at the service boundary. Requeueing
clears result/error and execution timestamps; claiming increments attempts and records time.
Failed transitions require a reason. Results are accepted only on completion or review.

Every transition increments a revision. The SQL adapter updates only the previously observed
revision and raises ConflictError if it changed. This prevents stale completion from overwriting
cancellation. Phase 2 claims use one conditional SQLite update with ordered selection, assigning
a worker ID, unique claim token and lease expiry. Completion verifies the active token and lease,
then uses the revision check. Handler code runs outside database transactions. Long handlers may
renew their lease through the execution context's heartbeat callback. Priority is 0–100, higher
first. Queue and lease indexes support polling and recovery.

An expired lease is requeued after a short delay when attempts remain, or marked FAILED when
exhausted. Handler exceptions follow the same bounded retry policy, using 1, 2, 4… seconds capped
at 60 seconds. Delayed jobs do not block other eligible jobs. The worker sleeps on an event while
idle and stops gracefully after the current job on Ctrl+C or SIGTERM. Only the three sample job
types have handlers; unsupported types fail explicitly.

The fake provider returns deterministic synthetic candidate facts in `result_json`. It makes no
network requests and does not persist or verify evidence. A review result stops at
WAITING_FOR_REVIEW; JobService.resume records `review_approved` and requeues it. This is not an
email authorization workflow. Phase 2 is at least once: a crash after an external side effect
could lead to a repeated handler call. Future side-effect handlers need stronger provider-level
idempotency. Long blocking calls must heartbeat before lease expiry; no heartbeat thread runs.
Creation calls a durable repository, not a broker. JobDispatcher describes optional future
post-commit wake-up hints; a reliable outbox/poller should relay them. This avoids broker-specific
logic in business services and prevents an unsafe database/broker dual-write assumption.

## Filesystem boundary

```text
workspace/universities/<safe-name>-<university-uuid>/
  university/
  admission/
  sources/
  professors/<safe-name>-<professor-uuid>/
    sources/
    research/
    study_plans/
    emails/
```

Names are normalized to ASCII slugs, sanitized and length-bounded; a full UUID suffix avoids
collisions and Windows device-name conflicts. Empty/non-Latin-only slugs get `entity` as a safe
fallback. Storage returns relative paths. Absolute paths, drive paths, parent traversal and
resolved symlink escapes are rejected. Directory creation is idempotent and never generates
study-plan/email files. A local trusted workspace is assumed; concurrent hostile filesystem
replacement is outside this adapter's scope.

Database transactions do not include filesystem writes. Workspace creation is explicit and
retryable after identity creation. No rename API exists; if one is later added, persist artifact
locations or implement an explicit workspace rename policy rather than recomputing old paths.

## Dependency choices

FastAPI/Pydantic provide REST contracts; SQLAlchemy/Alembic provide replaceable persistence and
migrations; Pydantic Settings handles configuration; Typer provides CLI. Uvicorn runs the API.
Development-only pytest/httpx exercise behavior and transport, Ruff handles lint/format, and mypy
checks source types. Standard logging replaces a logging framework. The worker runs only when
started by CLI; no orchestration framework, server database or container is required.

Implementation references: [uv projects](https://docs.astral.sh/uv/concepts/projects/),
[SQLAlchemy SQLite foreign keys](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support),
and [Alembic migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
