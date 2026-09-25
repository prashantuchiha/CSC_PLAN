# Phase 3 validation

Phase 3 extends the existing modular monolith. New application services cover Program,
ProfessorContact, Publication, StudyPlan, EmailRecord and ContactAttempt. ResearchIngestionService
coordinates source, professor, contact, fact and publication writes in one unit of work.
ResearchContextService provides bounded professor/university views, source references and
freshness queries. WorkspaceService writes only `notes.md` or `summary.md` under a known
professor's research folder.

The new migration is `c924ad29e762_source_identity.py`. It adds a nullable unique normalized URL
key, backfills historical sources, and preserves old duplicates and their foreign keys. The Phase 1
and 2 migrations are unchanged.

New files: `application/services/{normalization,records,ingestion,context}.py`,
`interfaces/mcp/{__init__,server}.py`, migration `c924ad29e762_source_identity.py`,
`tests/integration/test_phase3.py`, `scripts/demo_phase3.py`, ADR 003, this report, and the
captured demo JSON. Changed files include the Source entity/model, repository contracts and
implementations, evidence/identity/workspace services, Container, API schemas/dependencies/routes,
CLI, README, architecture overview/future integrations, `pyproject.toml`, and `uv.lock`.

The official Python MCP SDK runs as an independent stdio process. The 24 tools and two resources
are documented in README. Handlers call application services through Container; they do not
access SQLAlchemy, raw SQL or storage paths. FastAPI adds context/list/create routes for programs,
contacts and publications. CLI adds context/list commands and `mcp run`.

Validation commands, from the project root:

```powershell
uv sync --locked
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run alembic check
uv run python scripts/demo_phase3.py
uv run china-masters mcp run
```

The demo starts a real MCP stdio subprocess, invokes reads and mutations, queues two professor
jobs from different universities, and runs the separate worker once. Its disposable synthetic
database is removed after the run. Captured results are in `phase3-demo-output.json`; fake provider
facts remain `UNVERIFIED`.

Final checks: `83 passed, 1 skipped` in pytest; Ruff lint and format passed; mypy reported no
issues in 100 source files; Alembic upgrade succeeded and `alembic check` detected no new
operations. The demo persisted two universities, two professors, two sources, two facts, two
publications, one verified contact and two queued cross-university jobs. `worker once` completed
one queued job. The remaining job stays queued for a later worker run.

The server is idle when no host calls a tool, and it starts only on explicit launch. It adds the
MCP SDK and its transitive dependencies; it adds no browser, model, Redis, vector engine, HTTP MCP
listener or always-running process. Source content refresh/version history, human review policy,
and scalable indexed name matching remain future work. No email is sent by EmailRecord operations.

Recommended Phase 4: introduce a reviewed source-version/snapshot model, scale identity candidate
search with indexed lookup, and add explicit human approval rules before integrating any real
research provider. Keep provider clients outside domain and the existing service/UoW boundary.
