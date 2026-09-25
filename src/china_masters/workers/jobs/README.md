# Future job execution

Phase 2 includes the opt-in `JobWorker`, a handler registry and three synthetic handlers.
The worker claims through `JobExecutionService`, executes outside transactions, and sleeps
when idle. Start it with `china-masters worker run` or process one job with `worker once`.
No real external integration runs here. See `docs/architecture/adr-002-sqlite-jobs.md`.
