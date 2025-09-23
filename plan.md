# Current Architecture Snapshot
- **API & Services**: FastAPI app (`app/main.py`) exposes health probes plus domain routers for inventory, BOM/costing, analytics, planning, market data, systems metadata, rig lookups, UI state, and rate limiter metrics. Each router calls a service module that composes SQLAlchemy queries, Redis cache access, and math-core functions.【F:app/main.py†L1-L36】【F:app/api/__init__.py†L1-L23】
- **Math Core**: `indy_math` holds deterministic modules for consume-only costing, sell probability (SPP⁺), indicators, and the production planner. All modules accept explicit contexts so tests and workers can reuse them without side effects.【F:indy_math/costing.py†L1-L170】【F:indy_math/planner.py†L1-L120】
- **Persistence**: Alembic migrations provision core ledgers (`inventory`, `inventory_by_loc`, `acquisitions`, `consumptions`, `industry_jobs`, `buy_orders`, `orderbook_snapshots`, `consumption_log`), UI state, SDE subset tables (`type_ids`, `blueprints`, `rigs`, `structures`, `cost_indices`), and historical `market_snapshots`. Timestamp triggers and deterministic enums enforce consistency.【F:migrations/versions/20240416_01_initial_schema.py†L1-L170】【F:migrations/versions/20240416_02_sde_schema.py†L1-L200】
- **Caches & Background Work**: Redis caching (`app/cache.py`) provides TTL policies with last-good fallbacks, and APScheduler/Celery manage SDE autoload scans plus periodic price and indicator jobs. Rate limiting is centralized through `core.ratelimiter` with metrics exposed under `/metrics`.【F:app/cache.py†L1-L87】【F:app/sde_autoload.py†L77-L105】【F:app/rate_limit.py†L1-L49】

# Product Milestones & Status
| Milestone | Scope | Status | Notes |
| --- | --- | --- | --- |
| **Foundation** | Environment bootstrap, FastAPI skeleton, base schema, health probes | ✅ Complete | T-0001–T-0003 delivered requirements, app skeleton, and migrations; documentation and tooling are in place.【F:README.md†L1-L32】【F:migrations/versions/20240416_01_initial_schema.py†L1-L170】 |
| **Data & SDE Tooling** | SDE download/load CLIs, subset schema, auto-loader | ✅ Complete | `utils/fetch_and_load_sde.py`, subset migrations, and `app.sde_autoload` satisfy T-0034–T-0037/T-0039–T-0042. Remaining work is refining tests and docs (see backlog).【F:app/sde_autoload.py†L1-L105】【F:utils/fetch_and_load_sde.py†L1-L200】 |
| **Inventory & Costing** | Rolling-average ledger, WIP, BOM tree, costing, price history | ⚠️ In Progress | Services/endpoints exist (`/inventory/*`, `/bom/*`, `/prices/*`), but T-0077, T-0078, T-0047, and T-0048 stay open until determinism tests and coverage land. |
| **Market Analytics** | Indicators, SPP⁺, caching, rate limiter metrics | ⚠️ In Progress | `/analytics/*` and `/metrics` are live; Celery indicator recompute task is still a stub, and contract tests for providers remain to be written (T-0012, T-0049–T-0052). |
| **Planner & UI State** | Planner endpoints, systems/structures metadata, UI persistence | ⚠️ In Progress | Planner math is wired (`/plan/*`, `/systems`, `/structures/rigs`, `/state/ui`). Planner integration tests, frontend wiring, and UI polish tasks (T-0079–T-0083) remain open. |
| **Refactor Preparation** | Repository layer, cache abstraction, typed contracts | 🚧 Planned | Detailed below; tracked by new tasks T-0101–T-0104. |

# Near-Term Roadmap (Pre-Refactor)
1. **Stabilize Inventory & Costing math**
   - Finish determinism/fixture coverage for `indy_math.costing` and costing endpoints (T-0047, T-0048, T-0082).
   - Extend `/inventory/wip` tests to confirm ESI sync idempotency and reservations (T-0078).
2. **Harden Market Analytics**
   - Implement real indicator recompute worker and cache warming loops (T-0049–T-0052).
   - Add HTTP fixture tests for Adam4EVE/Fuzzwork adapters, ensuring rate-limit backoff paths (T-0012).
3. **Planner Integration & UI**
   - Provide API schemas (Pydantic models) for `/plan/*` and wire the React frontend selectors (T-0043–T-0046, T-0044, T-0045, T-0081).
   - Ensure planner output merges with inventory/WIP insights for coverage dashboards before UI polish.
4. **Operations Readiness**
   - Finalize `/metrics` expansion to include cache hit rates and worker heartbeat stats.
   - Document SDE autoload troubleshooting and offline workflows in docs/setup (extend T-0035/T-0037 docs commitments).

# Refactor Preparation Goals
To smooth the upcoming architecture refactor, we will:
- **T-0101 — Session Manager Extraction**: introduce a shared engine/session factory so services stop instantiating ad-hoc engines. Depends on completion of tests for inventory/costing to avoid regressions.
- **T-0102 — Cache Facade Cleanup**: wrap `CacheClient` access behind helper functions so services no longer call `_get_value`/`_set_value` directly. Enables pluggable caches and clearer metrics.
- **T-0103 — Repository Implementations**: create `app.repos.pg_inventory` and `pg_jobs` implementations that fulfill the protocol interfaces used by workers. This isolates SQL from business logic ahead of refactor.
- **T-0104 — API Contract Typing**: add request/response models for analytics, costing, and planner routes. Once types are in place we can generate client SDKs during the refactor.
These tasks can begin once the existing backlog achieves deterministic tests; no schema changes are anticipated, so risk to production data is low.

# Execution Details & Dependencies
- **Inventory & Costing**: T-0077 feeds T-0078 (WIP) and T-0082 (costing policy). Costing UI (T-0047/T-0048) should wait until math fixtures stabilize. `/bom/cost` already mixes rolling-average and spot pricing, so test scaffolding should reuse that implementation.【F:app/services/costing_service.py†L1-L109】
- **Market Data**: Historical price charts (T-0050–T-0052) rely on `market_snapshots` produced by `tasks.price_refresh`; ensure the worker runs with representative fixtures before UI binding.【F:tasks.py†L1-L55】
- **Planner Workstream**: T-0079 (weekly planner) and T-0080 (builder recommender) are partially realized by current planner endpoints but require validation of slot handling and overflow scheduling. Follow-up UI tasks (T-0081–T-0083) depend on these APIs plus inventory/WIP stability.
- **Frontend Integration**: Planner, BOM, and analytics endpoints expose JSON suited for TanStack Query; update `frontend` clients once API contracts are typed (future T-0104).

# Quality, Testing, and Ops Commitments
- Maintain unit/integration coverage for all ISK-impacting math. Golden fixtures for costing, indicators, planner windows, and SPP⁺ are mandatory before marking tasks done.
- Expand pytest suites to cover cache fallback paths, Redis outage tolerance, and Celery task idempotency (especially for price refresh and future indicator recompute).
- Linting (`ruff`) and formatting (`black`) remain mandatory per constitution; CI should enforce these before merges.
- Observability: extend `/metrics` after refactor to capture cache hit ratios, limiter saturation, and worker heartbeat counts so alerts can be defined.

# Risks & Mitigations (Updated)
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Incomplete math fixtures allow regressions during refactor | High | Prioritize T-0047/T-0048/T-0082 to lock down deterministic tests before touching service boundaries. |
| Redis/cache outages hiding stale data | Medium | Complete cache facade cleanup (T-0102) and ensure stale flags propagate to clients; document fallback behaviour. |
| Provider rate-limit violations during worker runs | Medium | Strengthen rate limiter metrics and add integration tests that simulate throttling (T-0012). |
| Planner/UI divergence | Medium | Ship typed contracts (T-0104) and automated contract tests linking backend outputs to frontend expectations. |

# Alignment with Tasks.md
- Backlog IDs referenced above correspond to `tasks.md` entries (T-0001–T-0083). Newly introduced refactor tasks T-0101–T-0104 should be appended to the backlog with dependencies noted below.
- Task ordering remains valid: foundational schema and environment tasks precede analytics/planner/UI work; new refactor tasks depend on stabilization work already captured in the backlog.
- Reviewed backlog remains consistent with this plan; no renumbering required. Update individual tasks with progress notes when determinism tests and contract coverage are added.
