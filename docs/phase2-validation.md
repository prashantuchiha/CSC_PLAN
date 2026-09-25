# Phase 2 validation

Validated on Windows with Python 3.12.14 and the existing uv environment. The Phase 1 project
was inspected and its baseline suite passed before implementation: 54 passed, one skipped.

| Check | Result |
|---|---|
| `uv run pytest -q` | 77 passed, 1 skipped, 1 warning |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 117 Python files already formatted |
| `uv run mypy` | No issues in 93 source files |
| `uv run alembic upgrade head` | Upgraded the existing Phase 1 database |
| `uv run alembic check` | No new upgrade operations detected |
| `uv run alembic current` | `ee8576e1a3fb (head)` |
| Phase 1 data check after upgrade | Existing university, two professors and two queued jobs retained |
| Phase 2 executable demo | Completed, retry, review and lease recovery confirmed |

The suite exercises competing claims against a temporary SQLite database, priority ordering,
delayed retries, exhausted attempts, lease expiry and renewal, stale worker rejection, handler
failure, unsupported job types, review resume, API/CLI compatibility, migration upgrade and
downgrade, and the repository/architecture tests from Phase 1. Direct SQL cannot mark a job
RUNNING without a lease. Tests never call a network provider.

The skipped test requires creating a directory symlink; this Windows environment denied it.
Starlette emits a deprecation warning for its installed httpx test-client integration. Neither
condition affects the worker or the passing tests.

The executed [Phase 2 demo snapshot](phase2-demo-output.json) was produced by
`uv run python scripts/demo_phase2.py`. It created a temporary SQLite database and used the
actual worker CLI. The snapshot shows:

- Professor job: QUEUED → COMPLETED with deterministic synthetic candidate facts.
- Transient failure: QUEUED with a future `next_attempt_at` → COMPLETED on attempt 2.
- Review: WAITING_FOR_REVIEW → resumed QUEUED → COMPLETED.
- Simulated process death: RUNNING claim → expired lease → recovered QUEUED → COMPLETED.

The fake provider used `example.invalid` URLs and did not persist verified facts or contact an
external service. The demonstration database was removed when the script exited. No worker or
API process was left running. Claim tokens are omitted from CLI and saved demo output.

## Manual validation

From this project directory in PowerShell, with uv installed:

```powershell
uv sync --locked
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run alembic check
uv run python scripts/demo_phase2.py
uv run china-masters worker once
```

The last command processes at most one job in the current configured database. To run the
continuous worker separately from the API, use `uv run china-masters worker run`; stop it with
Ctrl+C. The README shows how to create a professor research job and inspect it from the CLI.
