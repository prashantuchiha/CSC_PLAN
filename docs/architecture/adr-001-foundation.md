# ADR 001: Lightweight modular foundation

Status: Accepted for Phase 1.

Context: A personal research application will evolve across providers and interfaces on an older
laptop. It needs durable evidence and jobs, not distributed deployment infrastructure.

Decisions:

1. **Modular monolith.** One deployable Python package keeps deployment/debugging small while
   inward dependencies and separate modules protect business rules. Microservices would add
   network/operational cost without an independent scaling requirement.
2. **SQLite.** A local database supplies transactions, foreign keys and durable indexed state
   without a server. Its single-writer limit is acceptable for a personal application. Repositories
   and a unit-of-work port keep SQLAlchemy/session semantics out of business logic.
3. **Filesystem artifacts.** Documents/snapshots will be stored separately from structured state,
   addressed by safe relative keys through FileStorage. This avoids large database blobs and
   permits a later storage adapter. Backups must include both database and artifact root; there
   is no atomic transaction spanning them.
4. **Ports and adapters.** Expected replacements (database, file storage, AI, email, research,
   documents, dispatch) have explicit contracts. Concrete choices are wired in one composition
   root. Trivial pure functions do not gain unnecessary interfaces.
5. **No vector database initially.** Structured evidence and exact filtering are sufficient for
   the foundation. Embeddings and retrieval infrastructure require a demonstrated search need
   and can later be an adapter/index over the authoritative evidence store.

Resolved ambiguities: IDs are UUIDs; identifiers are distinct from names/slugs; contact methods
are a multi-row relation; only targeted job types accept entity IDs; batch creation is atomic;
review resume means requeue; job status changes are metadata only. Enums use readable text with
database checks, so adding values requires a deliberate migration. Basic entered metadata is
not automatically verified. Provenance supports all non-job domain entity types, while concrete
foreign keys and service checks protect different kinds of references.

Consequences: Integration namespaces are intentionally empty. Only requested identity/evidence/
job/workspace workflows have services. No generic CRUD HTTP API, plugin loader, event bus, queue
server, or frontend is invented. Future work can add focused services and adapter implementations
without moving business rules into interface handlers or changing the domain for provider SDKs.
