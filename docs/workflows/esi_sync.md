# ESI Sync Workflow

Purpose: keep `industry_jobs` and inventory reservations in sync with ESI while preserving idempotency and exactly-once semantics for inventory updates.

Key rules
- Respect ESI cache windows; do not spam endpoints outside their `Expires` period.
- Upsert jobs by `job_id`; status transitions allowed: `queued → active → delivered|cancelled`.
- Reservations: create/update on `queued|active`; release on `delivered|cancelled`.
- Settlement: on `delivered`, atomically move produced outputs to inventory (including excess capitalization) and post consumptions/fees within a single DB transaction.

Testability
- `app/workers/esi_sync.sync_industry_jobs` accepts injected `JobsRepo` and `InventoryRepo` Protocols to enable unit tests with fakes.
- Deterministic inputs produce deterministic upserts and inventory actions.

