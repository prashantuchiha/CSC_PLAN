# Phase 1 validation

Validated on Windows with Python 3.12.14. Dependencies were resolved and installed with uv;
the exact versions are recorded in `uv.lock`.

| Check | Result |
|---|---|
| `uv run pytest -q` | 54 passed, 1 skipped, 1 dependency warning |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 102 Python files already formatted |
| `uv run mypy` | No issues in 83 source files |
| `uv run alembic upgrade head` | Default SQLite database initialized |
| `uv run alembic current` | `506a9dad4b92 (head)` |
| `uv run alembic check` | No new upgrade operations detected |
| Upgrade → downgrade → upgrade | Passed against a temporary SQLite database |
| Real Uvicorn HTTP smoke check | Health, universities, professors, sources, facts, jobs and OpenAPI passed |

The skipped test attempts a directory symlink escape. This Windows environment denied symlink
creation, so that test could not exercise the condition. Other absolute-path, drive-path,
parent-traversal and unsafe-name tests passed. Starlette emitted a deprecation warning for its
httpx test-client integration; no test failed. No external provider/network research is used in
tests. The real HTTP smoke test used only a temporary localhost listener, stopped afterward.

Validation commands were run via uv during environment setup and via the resulting virtual
environment executables for checks; the commands above are their reproducible uv equivalents.

## Executed demonstration

`scripts/demo.py` created the following synthetic records in `data/china_masters.db`:

| Record | Count | Result |
|---|---|---|
| University | 1 | Demo University (synthetic) |
| Professors | 2 | Demo Professor One and Demo Professor Two |
| Source | 1 | Synthetic faculty profile at `example.invalid` |
| Research fact | 1 | Linked to professor and source; example verification metadata |
| Research jobs | 2 | Separate PROFESSOR_RESEARCH jobs, both QUEUED |
| Professor workspaces | 2 | Required subdirectories created |

The `VERIFIED_OFFICIAL` status in the fixture demonstrates a metadata workflow, not a real-world
verification. The sample URL is intentionally invalid. No AI, browser, email or document action
was performed.

University, professor and job records were retrieved through the installed Typer CLI. A real
Uvicorn process then served the same migrated database over localhost; HTTP reads confirmed
the university, professors, source, fact and both jobs. Full snapshots are saved in
[`demo-output.json`](demo-output.json) and [`api-demo-output.json`](api-demo-output.json).

## Delivery

The project directory includes its prepared environment, initialized demonstration database,
and empty professor artifact directories. The portable source ZIP excludes `.venv`, tool caches,
bytecode, the runtime database and generated workspace directories. On extraction, run
`uv sync --locked`, `uv run alembic upgrade head`, and `uv run python scripts/demo.py` to recreate
the working demonstration. No background process is left running.
