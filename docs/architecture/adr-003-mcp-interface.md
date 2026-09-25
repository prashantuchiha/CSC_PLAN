# ADR 003 — MCP is a local interface adapter

Status: accepted in Phase 3.

The MCP server runs independently over stdio using the official Python MCP SDK. It sits beside
FastAPI and Typer, with 24 bounded tools and two compact research resources. Each handler invokes
application services from the composition root. It does not import database repositories or
resolve filesystem paths. Expected domain failures become bounded MCP tool errors.

This keeps evidence validation, source deduplication, transactional ingestion and job creation
identical across clients. The service layer remains usable by future AI workers and frontends
without an MCP dependency. No network listener or idle daemon is started automatically.

Source URL identity is persisted as a nullable, unique normalized key. The new migration backfills
the first historical source for each normalized URL while preserving duplicate rows and foreign
keys. Source refresh/version history is deferred to a later phase; existing metadata is never
silently overwritten on reuse.
