# China Masters Research OS — Phase 3

A lightweight modular monolith for structured, evidence-linked university and professor research.
Phase 1 provides persistence, services, REST/CLI interfaces and durable job metadata. Phase 2 adds
a separate local worker, atomic SQLite claims, leases, recovery, bounded retries, typed handlers,
review gates and a deterministic fake research provider. The fake provider uses synthetic
`example.invalid` URLs and makes no network requests.

Phase 3 completes the research record services, adds transactional evidence-first ingestion,
compact context and freshness queries, safe professor notes, and an independent local MCP server.
MCP is an interface adapter alongside REST and CLI. It calls the same application services and
never opens database sessions or filesystem paths itself.

## Phase 3 research workflow

`ResearchIngestionService.ingest_professor_research` accepts a professor ID (or creates one),
source metadata, contacts, facts and publications in one unit of work. A failed reference or
validation rolls back the entire batch. ResearchFact retains its source ID and verification status;
conflicting claims remain separate facts. Intake only fills an empty existing canonical professor
field from an explicit `VERIFIED_OFFICIAL` fact backed by an official source. Manual professor
edits use an explicit update service. The fake provider's candidate facts are ingested as
`UNVERIFIED` in the disposable Phase 3 demo.

For example, ingest an official faculty source and an `interest` fact using the same source URL.
The fact points to the returned Source ID; the professor context returns both the claim and source
reference. A secondary or unverified claim about the same field remains another fact and does not
replace the canonical professor record.

Source identity conservatively lowercases HTTP(S) scheme and host, removes default ports and
fragments, and uses `/` for an empty path. It retains query strings and path case. The first source
for a normalized URL is reused without overwriting its retrieval time, title, type, publisher,
domain, hash or snapshot path. New adapters should compare content hashes and store refreshed
snapshots/version history in a future SourceVersion record; they must not silently rewrite the
original provenance. Migration 3 backfills URL keys; historical duplicates remain intact with
the first keyed record available for reuse.

Professors have English/Chinese names, university and department. Public academic identifiers
and official email fit ProfessorContact types (ORCID, DBLP, Semantic Scholar, EMAIL, etc.).
`search_professors` matches names, profile URL and contact values but does not merge similar names.
Callers should inspect candidates and supply an explicit professor ID to update an existing record.

Professor context includes bounded facts, verified contacts, recent publications, sources,
study-plan metadata and outreach status; university context includes bounded programs, admission
facts, professors and sources. Default publication/source limits are 10; each limit has a hard cap.
Freshness queries use verified fact timestamps and existing professor/program verification dates;
records without verification are stale. This is a query, not a scheduled refresh process.

Research notes live under the professor workspace as `research/notes.md` or
`research/summary.md`, through FileStorage. The note service accepts only those two names and
at most 100 KB. Structured database records remain canonical.

## Local MCP server

Launch only when needed, from the project root after `uv run alembic upgrade head`:

```powershell
uv run china-masters mcp run
```

The server uses the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
over stdio. Configure an MCP client to launch this command with the project as its working
directory; stdout is reserved for MCP messages. There is no HTTP MCP listener and the FastAPI
process does not start MCP.

The 24 tools are grouped by purpose:

| Area | Tools |
|---|---|
| Universities | `search_universities`, `get_university`, `create_university`, `update_university`, `get_university_research_context` |
| Professors | `search_professors`, `list_professors`, `get_professor`, `create_professor`, `update_professor`, `get_professor_research_context` |
| Research | `ingest_professor_research`, `add_source`, `add_research_fact`, `add_publication`, `add_professor_contact`, `get_professor_sources` |
| Workflow | `create_research_jobs`, `get_jobs`, `get_job`, `get_pending_research`, `get_stale_research` |
| Files | `create_professor_workspace`, `save_professor_research_notes` |

Two bounded resource templates are available:
`research://professors/{professor_id}` and `research://universities/{university_id}`.
All tool IDs are UUID typed. Reads and mutations are separate. No SQL execution, unrestricted
path write, web lookup or job execution tool is exposed.

A typical MCP session calls `search_professors` to inspect possible duplicates, then
`ingest_professor_research` with source URLs, facts and publication data, followed by
`get_professor_research_context`. It can queue `create_research_jobs` for professors at several
universities in one request. The independent worker processes those jobs later.

Useful REST additions include `GET /professors/{id}/context`, `/contacts`, `/publications`,
`GET /universities/{id}/context`, `/programs`, and create endpoints for contacts, publications
and programs. CLI adds `professor context|contacts|publications`, `university context`, and
`mcp run`. All use application services.

For a disposable end-to-end demonstration, run:

```powershell
uv run python scripts/demo_phase3.py
```

It creates two synthetic universities and professors, persists official-style and unverified fake
evidence, starts a real stdio MCP subprocess, calls read and mutation tools, queues cross-university
jobs, writes a note, and runs `worker once`. It uses a temporary database and performs no network
research. See `docs/phase3-demo-output.json` for a captured run.

## Run from a fresh checkout

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available.
On Windows PowerShell, the official installation command is:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new terminal after installation, change into this project directory, and run:

```powershell
uv sync --locked
uv run alembic upgrade head
uv run china-masters health
uv run uvicorn china_masters.interfaces.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Start the worker in a **separate terminal** from the project root when you want queued jobs
processed. The API does not start it:

```powershell
uv run china-masters worker run
```

Ctrl+C stops the worker. For one eligible job and a clean exit, use
`uv run china-masters worker once`. The worker sleeps between empty polls.

The project pins Python 3.12 in `.python-version`; uv can obtain it if needed. Python 3.12+
is supported by the package. `uv.lock` records the exact dependency resolution used for validation.
Only one API process is needed; omit reload and multiple workers on an older laptop.

Open [interactive API docs](http://127.0.0.1:8000/docs) or [health](http://127.0.0.1:8000/health).
Ctrl+C stops the API. Neither API nor worker is installed as a background service.

In the already prepared delivery directory, the virtual environment is ready. Without installing
uv globally, you can launch it immediately with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn china_masters.interfaces.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

The included `.venv` is machine-specific. Recreate it with `uv sync --locked` after moving the
project or extracting the source archive; the archive intentionally excludes environments/caches.

## Configuration

Copy `.env.example` to `.env` or set environment variables. Paths are relative to the process's
working directory; run commands from the project root. No absolute machine paths are in source.

| Variable | Default | Meaning |
|---|---|---|
| `CM_DATABASE_URL` | `sqlite:///data/china_masters.db` | SQLAlchemy database URL |
| `CM_WORKSPACE_ROOT` | `workspace` | Local artifact root |
| `CM_LOG_LEVEL` | `INFO` | Standard logging level |
| `CM_LOG_JSON` | `false` | JSON logs instead of text |
| `CM_JOB_MAX_ATTEMPTS` | `3` | Maximum claims per job, including retries |
| `CM_JOB_POLL_INTERVAL_SECONDS` | `2.0` | Idle worker wait interval |
| `CM_JOB_LEASE_SECONDS` | `300` | Claim lifetime before recovery |

SQLite foreign keys are enabled on **each connection**. A 10-second busy timeout handles brief
write contention. The API never creates tables at startup: schema changes run through Alembic.
`/health` and CLI `health` report process liveness; listing universities checks database readiness.
SQLite is the only implementation tested; a future database may need a driver, dialect-specific
integrity-error translation, and migration adjustments inside infrastructure.

## Demo and CLI

```powershell
uv run python scripts/demo.py
uv run china-masters university list
uv run china-masters professor list
uv run china-masters job list
uv run china-masters worker once
uv run china-masters --help
```

The demo creates one university, two professors, one source, one linked research fact, professor
workspaces, and two independent professor-research jobs. It uses synthetic names and
`example.invalid` URLs. Its `VERIFIED_OFFICIAL` label only demonstrates the data model; **none of
the demo data is a real verified university claim**. The script can be rerun without duplicating
its fixture records. `docs/demo-output.json` records the executed demo; `docs/validation.md`
records the validation performed.

Additional commands:

```powershell
uv run china-masters university create "My University"
uv run china-masters university get UNIVERSITY_UUID
uv run china-masters professor create UNIVERSITY_UUID "Professor Name"
uv run china-masters professor workspace PROFESSOR_UUID
uv run china-masters job create PROFESSOR_RESEARCH --entity-id PROFESSOR_UUID --entity-id ANOTHER_PROFESSOR_UUID
uv run china-masters job cancel JOB_UUID
uv run china-masters job transition JOB_UUID RUNNING
uv run china-masters job get JOB_UUID
uv run china-masters job resume JOB_UUID
uv run china-masters worker recover
```

Replace uppercase UUID placeholders with IDs returned by prior commands. The retained manual
transition command gives manually RUNNING jobs a lease; a worker-owned RUNNING job can only be
completed by its worker. Manual transitions never invoke external integrations.

## Phase 2 job execution

Create a synthetic professor research job from the CLI:

```powershell
uv run china-masters university create "Example University"
uv run china-masters professor create UNIVERSITY_UUID "Example Professor"
uv run china-masters job create PROFESSOR_RESEARCH --entity-id PROFESSOR_UUID
uv run china-masters job list
uv run china-masters worker once
uv run china-masters job get JOB_UUID
```

The first job read shows `QUEUED`; after `worker once` it shows `COMPLETED` and a synthetic
`result_json`. For a repeatable full demonstration including retry, review and recovery, run:

```powershell
uv run python scripts/demo_phase2.py
```

This script creates a disposable temporary SQLite database, invokes the actual worker CLI,
prints each state and removes the demo database afterward. The executed result is saved in
[`docs/phase2-demo-output.json`](docs/phase2-demo-output.json).

The execution path is:

```text
API or CLI creates job → SQLite queue → worker claims → typed handler
    → fake provider → structured result → COMPLETED or WAITING_FOR_REVIEW
```

Handlers exist for `PROFESSOR_RESEARCH`, `UNIVERSITY_RESEARCH` and
`GENERAL_CSC_RESEARCH`. Other existing job types remain creatable, but the worker marks them
`FAILED` with an explicit unsupported-handler error. It never silently drops or executes them.
The fake provider returns candidate facts only in the job result; it does not mark them verified
or insert them into the evidence tables. Future handlers can call the provided `heartbeat()`
during long work to extend their lease.

`worker once` first recovers expired leases, then claims at most one eligible job. A claim uses
one conditional SQLite update, increments `attempts`, and writes a worker ID, unique claim token
and lease expiry. A cancellation, expiry or new claim invalidates stale completion. Handler
exceptions log a traceback, store a bounded 500-character error and schedule retry after 1, 2,
4… seconds, capped at 60 seconds. Exhausted jobs become `FAILED`; unsupported types fail
immediately. A delayed job does not block other eligible jobs. `worker recover` only recovers
expired claims and does not execute jobs.

For development, `--payload-json` accepts a JSON object. Known keys for the three sample
handlers are validated: `focus` (professor/university), `filters` (professor string list),
`topic` (general CSC), `review_required` (boolean), and `fail_until_attempt` (integer used
only to demonstrate retry). Unknown keys are preserved for compatibility with Phase 1 jobs.
For example, pass `--payload-json '{"review_required":true}'` in a shell that preserves the
JSON quotes. On Windows PowerShell, `scripts/demo_phase2.py` avoids quoting differences.

A review result stops at `WAITING_FOR_REVIEW`. `job resume JOB_UUID` or
`POST /jobs/{id}/resume` records review approval and requeues the same job; the sample handler
then completes. This operation does not authorize email sending. Review approval and provider
side-effect policies for real integrations require a later phase.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| GET, POST | `/universities` | List/create universities |
| GET | `/universities/{id}` | Get one university |
| GET | `/universities/{id}/professors` | List associated professors |
| POST | `/universities/{id}/workspace` | Ensure workspace exists |
| GET, POST | `/professors` | List/create professors |
| GET | `/professors/{id}` | Get one professor |
| POST | `/professors/{id}/workspace` | Ensure workspace exists |
| POST | `/sources` | Add source metadata |
| GET | `/sources/{id}` | Get a source |
| GET, POST | `/research-facts` | List/add provenance facts |
| GET, POST | `/jobs` | List/create jobs, including batches |
| GET | `/jobs/{id}` | Get one job |
| POST | `/jobs/{id}/cancel` | Cancel, idempotently if already cancelled |
| POST | `/jobs/{id}/resume` | Record review approval and requeue a review-gated job |
| POST | `/jobs/{id}/transition` | Manual metadata transition for debugging |

Lists accept `limit` (1–500, default 100) and `offset` (default 0). Job lists also accept `status`;
filtered jobs are ordered by descending priority, then creation time and ID. Other lists use ID
order. Job creation **always returns an array**, including single-job requests. A batch is atomic.
Job inspection includes worker ID, lease expiry and next retry time. The claim token stays private.
HTTP 404 means a requested record is missing; 422 means invalid input/reference/state transition;
409 means a constraint or optimistic-concurrency conflict. Unexpected errors use a generic 500.

Example batch body for `POST /jobs`:

```json
{
  "job_type": "PROFESSOR_RESEARCH",
  "entity_ids": ["<professor-uuid-from-university-a>", "<professor-uuid-from-university-b>"],
  "priority": 20,
  "payload_json": {"focus": "recent publications"}
}
```

`entity_type` is inferred for targeted jobs. Single-target requests may use `entity_id` instead
of `entity_ids`, but never both. Duplicate IDs, empty explicit batches, mismatched target types,
unknown targets, and batches over 500 are rejected. Independent jobs may span any universities.

| Job types | Required target |
|---|---|
| `GENERAL_CSC_RESEARCH`, `UNIVERSITY_DISCOVERY`, `INBOX_SYNC` | Global; omit entity type and IDs |
| `UNIVERSITY_RESEARCH`, `PROFESSOR_DISCOVERY` | University |
| `PROGRAM_RESEARCH` | Program |
| `PROFESSOR_RESEARCH`, `PROFESSOR_PUBLICATION_RESEARCH`, `STUDY_PLAN_GENERATION`, `EMAIL_DRAFT` | Professor |
| `EMAIL_SEND` | Email record (metadata only) |

## Database tables

`universities`, `programs`, `professors`, `professor_contacts`, `sources`, `research_facts`,
`publications`, `study_plans`, `email_records`, `contact_attempts`, `research_jobs`, plus Alembic's
`alembic_version`. All 11 domain tables have repository contracts and SQLAlchemy implementations.
Programs, contact methods, publications, plans, email records, and outreach attempts have domain
models and repositories; their full CRUD service/API workflows are intentionally deferred.

## Project structure

```text
src/china_masters/
  bootstrap.py                 composition root and application-scoped engine
  domain/
    entities/                  one framework-free dataclass module per entity
    enums/                     contact, source, verification and workflow states
    value_objects/             UTC and JSON values
    repositories/              repository contracts
    exceptions/                business/boundary exceptions
  application/
    services/                  university, professor, evidence, workspace, job execution services
    commands/                  CreateJobs
    queries/                   pagination
    dto/                       typed job payloads, execution result/context
    ports/                     unit of work, job handler and provider contracts
  infrastructure/
    database/
      models/                  separate SQLAlchemy models
      repositories/            adapters and domain/model mapping
      migrations/              initial schema and Phase 2 lease migration
      engine.py                SQLite configuration
      unit_of_work.py          commit/rollback and session lifetime
    filesystem/                local FileStorage adapter
    configuration/             Pydantic Settings
    logging/                   standard logging configuration
  adapters/research/fake.py    deterministic provider, no network
  adapters/{ai,email,documents}/  future extension namespaces
  interfaces/api/routers/      FastAPI transport and validation
  interfaces/cli/              Typer commands using the same services
  workers/jobs/                registry-driven worker and sample handlers
tests/{unit,integration}/
scripts/{demo,demo_phase2}.py
data/china_masters.db
workspace/universities/
docs/architecture/{overview,future-integrations,adr-001-foundation,adr-002-sqlite-jobs}.md
```

## Development and validation

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run alembic check
```

Tests migrate temporary SQLite databases, exercise all repository types, validate API/CLI
workflows, prove rollback/foreign-key behavior, and check architecture import boundaries. Phase 2
tests cover concurrent claims, retry timing, exhausted attempts, stale ownership, lease renewal,
crash recovery, review resume, unsupported handlers and an idle worker. Unit tests use pure
entities and a fake unit of work; no tests call external providers. The symlink
escape test skips when Windows denies symlink creation. The installed Starlette version emits a
test-client deprecation warning for `httpx`; runtime behavior and the tests pass.

Create later migrations with `uv run alembic revision --autogenerate -m "description"`, inspect
the generated migration, and run `uv run alembic upgrade head`. Never edit a deployed historical
migration or use `Base.metadata.create_all()` as a migration substitute.

## Current limits

This is a local, single-user application without authentication; bind to localhost. One worker
process is the supported deployment shape. There is no real AI, browsing, Graph, email sending,
DOCX, MCP, frontend, Redis, Celery, Docker or vector store. Only the three sample job types have
handlers and typed payload validators. Evidence status is asserted by the caller;
the application checks source categories but cannot verify external content. Facts remain
separate from canonical entity fields, so conflicts are preserved instead of silently overwriting
research. Filesystem work and database commits are separate retryable operations.
Claims provide at-least-once execution: a handler can run twice after a crash or lease expiry.
Long handlers must heartbeat before the lease expires. There is no automatic timer-based heartbeat
or exact-once side-effect guarantee. Future email sending requires provider-level idempotency,
approved content, and stronger authorization. See
[future integrations](docs/architecture/future-integrations.md).
