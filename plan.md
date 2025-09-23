# Architecture Overview
- React SPA (inventory dashboards, SPP⁺ controls) talks to a FastAPI service tier over HTTPS; the API brokers all reads/writes to durable stores and exposes deterministic math-core outcomes.
- FastAPI layer coordinates with Postgres (durable state: inventory, jobs, orders, telemetry) and Redis (ephemeral caches, job queues). Domain services invoke pure math-core functions for costing, SPP⁺, and indicators; math modules never reach outside their injected inputs.
- Celery worker pool executes asynchronous syncs (ESI, price refresh, indicator recompute) and long-running math tasks. APScheduler seeds recurring tasks into Celery.
- Provider adapters (ESIClient, Adam4EVEProvider, FuzzworkProvider) encapsulate all external calls with retries, backoff, and circuit-breakers; they publish data back through Redis + Postgres snapshots.
- Stateless math core is packaged as a Python module (`indy_math`) consumed by API and workers. All stateful concerns (inventory reservations, caches, preferences) reside in FastAPI service/DB layers per constitution.

# Domain Model & Schema (initial migrations)
| Table | Columns (type) | Keys & Indexes | Primary Workflows |
| --- | --- | --- | --- |
| `inventory` | owner_scope (text), type_id (int4), qty_on_hand (numeric), avg_cost (numeric), updated_at (timestamptz) | PK `inventory_pkey(owner_scope, type_id)`; index on `(owner_scope, avg_cost)` for reporting | Rolling-average valuation per item at corp+alts scope. |
| `inventory_by_loc` | owner_scope, type_id, location_id (bigint), qty_on_hand, qty_reserved, qty_in_transit, updated_at | PK `(owner_scope, type_id, location_id)`; partial index on `qty_reserved > 0` | Location buckets (On-hand prod, At Jita incl. in-transit, Open Buy Orders intent). |
| `acquisitions` | id (uuid), ts, owner_scope, type_id, qty, unit_cost, source(enum: market, industry_excess, contract), location_id, ref_job_id, ref_order_id | idx on `(owner_scope, ts DESC)`; FK `ref_job_id` → `industry_jobs`, `ref_order_id` → `buy_orders` | Rolling-average updates on acquisitions; audit trail. |
| `consumptions` | id (uuid), ts, owner_scope, type_id, qty, reason(enum: job_run, writeoff), location_id, ref_job_id | idx `(ref_job_id, type_id)`; FK to `industry_jobs` | Consume-only costing ledger feeding job cost reports. |
| `industry_jobs` | job_id (bigint), char_id (bigint), type_id, activity(enum), runs(int), start_time, end_time, output_qty, status(enum queued/active/delivered/cancelled), location_id, facility_id, fees_isk(numeric) | PK job_id; idx `(status, end_time)` for scheduling; idx `(owner_scope, status)` via view (owner derived) | Reservations, WIP tracking, lead-time inputs for SPP⁺. |
| `buy_orders` | order_id (bigint), owner_scope, type_id, location_id, region_id, price(numeric), remaining_qty, issued_ts, last_seen_ts, status(enum open/filled/cancelled) | PK order_id; idx `(owner_scope, status)`; idx `(type_id, region_id)` | Drives Open Buy bucket and replenishment signals. |
| `orderbook_snapshots` | id (uuid), ts, region_id, type_id, side(enum bid/ask), best_px, best_qty, depth_qty_1pct, depth_qty_5pct, stdev_pct | idx `(type_id, region_id, ts DESC)`; uniqueness constraint `(region_id, type_id, side, ts)` | Inputs to indicators, depth awareness for SPP⁺. |
| `consumption_log` | id (uuid), ts, owner_scope, type_id, qty, location_id, ref_job_id, note(text) | idx `(ts DESC)`; FK `ref_job_id` | Immutable audit of reservations released/consumed (distinct from aggregate `consumptions`). |

Migration checklist:
- [ ] All monetary fields use `NUMERIC(28,4)`; quantities use `NUMERIC(20,2)`.
- [ ] Add `created_at`/`updated_at` triggers via `pg_timestamps` extension.
- [ ] Views: `inventory_coverage_view` aggregating `inventory_by_loc` buckets for API.
- [ ] Ensure referential integrity with `ON UPDATE CASCADE` for dependent IDs from ESI.

# Core Algorithms ("math core")
```python
@dataclass(frozen=True)
class CostResult:
    consumed_cost: Decimal
    consumed_qty: Decimal
    excess_to_inventory: Mapping[int, Decimal]
    fee_split: Mapping[str, Decimal]
    trace: CostTrace

def cost_item(type_id: int, qty_needed: int, ctx: CostContext) -> CostResult:
    """Pure function: greedy integer batches, consumes inventory before triggering make/buy recipes."""
```
- Inputs: `CostContext` supplies immutable snapshots (inventory levels, blueprints, bill-of-materials, fee schedule, rolling averages). No DB or network access.
- Invariants:
  - Never mutate context; return new structures only.
  - Consume On-hand inventory first; recurse into production steps for deficits using make recipes; respect integer batch size per tier.
  - Calculate job fees on executed runs, divide fees between consumed outputs and excess outputs proportional to units produced.
  - Excess outputs appear in `excess_to_inventory` with unit costs derived from allocated inputs + fee share (capitalized into inventory on application layer).
  - Emit `trace` covering inputs, valuations, and recursion path for UI explainability.

```python
def spp_lead_time_aware(
    depth_ahead_now: int,
    dv_forecast_fn: Callable[[datetime], DepthForecast],
    lead_time_days: Decimal,
    horizon_days: Decimal,
    price_best_now: Decimal,
    drift_rate: Decimal,
    price_policy: PricePolicy,
    spread_at_list: Decimal,
    vol_stdev_at_list: Decimal,
) -> SPPResult:
    """Pure forecast: project queue depth to listing time, adjust for drift, output SPP⁺ and diagnostics."""
```
- Steps: roll queue forward `lead_time_days`, adjust bid/ask via drift, apply demand depletion minus new listings estimate, compute probability-of-sale multipliers (PAM, LSM, VOLP).
- Deterministic outputs for identical inputs; uses injected deterministic `dv_forecast_fn`.

Indicator utilities:
- `moving_average(series: Sequence[Decimal], window: int) -> Decimal`
- `bollinger_bands(series, window, k) -> BollingerResult`
- `shallow_depth_metrics(orderbook_slice) -> DepthSummary`
- All functions pure; raise `ValueError` on insufficient data to enforce guardrails.

Unit-testing commitments:
- [ ] Golden-master fixtures for `cost_item` covering consume-only, recursion, excess capitalization edge cases.
- [ ] Determinism tests with identical contexts to prove repeatability.
- [ ] Boundary tests for SPP⁺ (zero depth, surge depth, negative drift bounded).

# External Providers (adapters)
```python
class PriceProvider(Protocol):
    def get(self, type_id: int, region_id: int) -> PriceQuote: ...

class ESIClient(Protocol):
    def list_industry_jobs(self, owner_scope: str) -> Sequence[ESIJob]: ...
    def list_assets(self, owner_scope: str) -> Sequence[ESIAsset]: ...
    def get_system_cost_indices(self, system_id: int) -> Sequence[CostIndex]: ...
    def get_character_skills(self, char_id: int) -> ESISkills: ...
```
- Retry policy: exponential backoff (base 1.5s, max 5 attempts) with full jitter, circuit-breaker trips after 3 consecutive failures per provider per region.
- Provider selection: Adam4EVE primary → Fuzzwork fallback; if both fail, serve last-good cached value with staleness flag.
- Caching TTLs: prices 15m, indices 24h, skills/jobs respect ESI `Expires` header (persist metadata in Postgres).
- Token handling: adapters require injected token storage service (encrypted secrets) and refresh automatically prior to expiry.

Checklist:
- [ ] Wrap adapters with metrics (latency, retries, last_success_ts).
- [ ] Reject responses failing schema validation before entering math core.

# API Surface (FastAPI)
| Endpoint | Verb | Request | Response (200) | Notes |
| --- | --- | --- | --- | --- |
| `/state/ui` | GET | query: optional `owner_scope` | `{ "owner_scope": str, "last_sync": {...}, "widgets": {...} }` | Returns cached UI state; 200 w/ ETag; 401 if token invalid. |
| `/sync/snapshot` | GET | none | `{ "prices": {"ts": iso8601, "stale": bool}, "indices": {...}, "esi_jobs": {...} }` | Triggers async refresh when stale; respond 202 with `Location` header when refresh queued. |
| `/inventory/coverage` | GET | query: `owner_scope` | `{ "buckets": [{"location": "OnHand", "qty": Decimal, "days": Decimal}, ...], "valuation": {...} }` | Aggregates from `inventory_by_loc` + rolling average; supports pagination via `cursor` for large item sets. |
| `/plan/next-window` | POST | `{ "start": iso8601, "duration_hours": int, "owner_scope": str }` | `{ "characters": [{"char_id": int, "recommended_jobs": [...]}], "assumptions": {...} }` | Runs math core scheduling; returns 422 on invalid window; 409 if reservations conflict. |
| `/analytics/indicators` | GET | query: `type_id`, `region_id`, optional `window` | `{ "ma": Decimal, "bollinger": {...}, "volatility": {...} }` | Serve from Redis cache backed by Postgres; 429 when rate limit hit. |
| `/analytics/spp_plus` | POST | `{ "type_id": int, "region_id": int, "lead_time_days": Decimal, "horizon_days": Decimal, "batch_options": [int] }` | `{ "spp": Decimal, "recommended_batch": int, "diagnostics": {...} }` | Deterministic math output; 400 if insufficient depth data; 503 when providers unavailable but no last-good cache. |

Error envelope: `{"error": {"code": str, "message": str, "details": object}}`; include correlation `request_id` header.

# Workers & Schedules
| Task | Cadence | Executor | Idempotency & Notes |
| --- | --- | --- | --- |
| Price refresh per provider/region | Every 12 minutes staggered | Celery beat → Celery worker | Use provider priority queue, skip if cache younger than TTL, store last-good. |
| System cost index refresh | Daily at 11:00 EVE | APScheduler → Celery | Pull ESI with cache headers, upsert snapshot. |
| ESI jobs sync | On login event + every 30 minutes | Celery (per owner) | Compare `job_id` delta; idempotent via upsert + status transitions. |
| ESI assets sync | Every 60 minutes or manual trigger | Celery | Respect ESI `pages`; dedupe via asset ID; update reservations. |
| Indicator recompute | Hourly | Celery | Rebuild metrics from latest orderbook snapshots; publish to Redis. |
| Discord alerts | Every 15 minutes | Celery | Send when profitability threshold breached or coverage < target; ensure once-per-hour per signal. |

Checklist:
- [ ] All schedules respect constitution’s polite cadence (no rate limit violations).
- [ ] Worker tasks wrap DB ops in transactions and retry with backoff.

# Caching & Performance
- Redis keys: `price:{provider}:{region}:{type}` (TTL 900s), `index:{system}:{activity}` (TTL 86400s), `indicator:{region}:{type}` (TTL 3600s), `spp:{type}:{region}:{lead}:{horizon}:{batch_hash}` (TTL 1800s).
- Use `SETEX` with atomic writes; track staleness metadata in Postgres for audit.
- Cache-aside strategy with last-good fallback; API returns cached 200 within 150 ms P95; on cache miss, dispatch async refresh and serve 202 or last-good (≤100 ms).
- Inventory mutations executed via Postgres transactions with `SELECT ... FOR UPDATE` on `inventory`/`inventory_by_loc` rows to guarantee exactly-once updates.
- Profile math core to ensure pure functions execute in <25 ms per batch under median scenarios; memoize blueprint trees within request context only (no globals).

## Rate Limits & Provider Guardrails
- Central RateLimiter (token bucket) tracks calls per provider/endpoint with configurable capacity and refill rates per provider (e.g., ESI per-route, Adam4EVE polite 10s, Fuzzwork regional intervals).
- Adapters call `RateLimiter.block_until_allowed(key)` before outbound requests; retry with exponential backoff and circuit breakers remain in place.
- Emit basic counters per key: `allowed`, `denied`, `delayed`; expose via metrics endpoint later.
- Configuration: env-driven defaults; tune per environment without code changes.

## SDE Update Workflow (Dev-only)
- SDE Manager (`python utils/manage_sde.py update --from-file path/to/sde.yaml`) parses only required subsets (T2 frigates/cruisers; reaction chains; relevant structures, rigs; system/region/constellation IDs) into compact JSON or inserts into Postgres.
- Store artifacts under `data/sde/` (gitignored). Production images never bundle raw SDE; developers refresh locally when CCP publishes new drops.
- Schema added for SDE subsets: `type_ids`, `blueprints`, `structures`, `cost_indices` for convenience joins; migrations are idempotent and versioned.

# Security, Secrets, and Tokens
- Store ESI refresh/access tokens encrypted (e.g., envelope encryption with KMS); rotate tokens every 30 days or on scope change.
- Secrets injected via environment variables or secret manager; `.env` files excluded from VCS.
- Enforce least-privilege ESI scopes: Industry jobs, Assets, Skills; no wallet scope stored.
- Append immutable audit log entries on inventory changes and job status transitions with actor, request_id, timestamp.
- Harden FastAPI with OAuth2 client credentials for UI/worker access; require HTTPS everywhere.

# Environment & Tooling
- Python virtual environment named `IndyCalculator`; configure VS Code interpreter to `.venv/IndyCalculator/bin/python`.
- Core dependencies (requirements.txt pinned): FastAPI, Uvicorn[standard], SQLAlchemy, Alembic, Pydantic, Celery, APScheduler, Redis-py, Pandas, NumPy, statsmodels, scikit-learn (for basic regressions), httpx, tenacity, pytest, pytest-asyncio, coverage, black, ruff.
- Frontend stack: React 18, Vite, TypeScript, TanStack Query, Tailwind (optional), recharts/d3 for visualizations.
- Tooling checklist:
  - [ ] `ruff` lint on pre-commit (constitution requirement).
  - [ ] `black` formatting pipeline.
  - [ ] Docker Compose for Postgres + Redis with named volumes.
  - [ ] `.gitignore` excludes `IndyCalculator/`, `.env*`, `__pycache__/`.

# Testing Strategy
- [ ] Unit tests cover 100% of ISK-affecting formulas (costing, SPP⁺, indicators) with golden fixtures.
- [ ] Determinism tests execute math core twice with identical inputs and assert stable outputs.
- [ ] Contract tests for Adam4EVE/Fuzzwork adapters using recorded HTTP fixtures (pytest + vcr.py); include rate-limit handling cases.
- [ ] API tests (pytest + httpx) for happy paths, validation errors (422), and provider outage fallbacks (503 with last-good data).
- [ ] Integration tests via Docker Compose bring-up (Postgres, Redis) with seeded inventory/jobs to validate reservations and excess capitalization flows.
- [ ] Load smoke: ensure price/index read paths stay <150 ms P95 using locust/k6 against cached scenarios.

# Deployment & Ops
- Containerize API, worker, and frontend; multi-stage Dockerfile with poetry/pip install inside `IndyCalculator` venv.
- Compose file for local dev; production helm/k8s optional but container-ready for Fly.io/App Runner.
- Config through environment variables; secrets supplied via platform secret manager.
- Health endpoints: `/health/live`, `/health/ready`, `/health/startup`; workers expose Celery heartbeat metrics.
- Target infra: API on Fly.io or AWS App Runner, Postgres on Neon or RDS, Redis on Upstash or Elasticache, frontend on Vercel/Netlify.
- Observability: structured JSON logs with request_id, user_scope; metrics emitted to Prometheus-compatible endpoint (`/metrics`) for scraping; alerts on provider failure rate, queue backlog, cache hit ratio.

# Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Provider downtime (Adam4EVE/Fuzzwork) | Stale pricing → bad recommendations | Cache last-good, fallback across providers, alert on staleness >30m. |
| ESI rate limits / cache windows | Sync failures → inventory drift | Honor `Expires`, throttle per token, expose manual retry with backoff scheduler. |
| Data drift from EVE SDE updates | Incorrect blueprint/cost data | Version blueprint refs, schedule SDE ingest job with migration script review. |
| Math core regressions | Financial misstatements | Golden fixtures + determinism tests in CI; require code review from math owner. |
| Queue overruns (Celery) | Delayed signals | Autoscale worker, prioritize critical queues, add circuit breaker on long tasks. |

# Milestones & Exit Criteria
| Phase | Focus | Deliverables & Acceptance | Demo Scenario |
| --- | --- | --- | --- |
| MVP | Inventory & costing foundation, price cache, indicators, `/analytics/spp_plus`, basic React UI | ✓ Inventory CRUD with rolling averages; ✓ consume-only costing reflections; ✓ price cache & indicators API; ✓ deterministic SPP⁺ output; ✓ UI dashboard with coverage bars | Walk through acquiring ore, running job, showing cost trace and SPP⁺ batch recommendation aligning with specs. |
| Phase 2 | Reservations/WIP, batch optimizer, alerting | ✓ Job reservation workflow from ESI sync; ✓ batch optimizer honoring integer constraints; ✓ Discord alerts for low coverage/profit swings | Demo multi-character plan window recommending balanced queues and sending alert on low Jita stock. |
| Phase 3 | Advanced depth modeling, schedule-aware comparisons, corp-scale ops | ✓ Enhanced depth metrics in SPP⁺; ✓ schedule-aware comparisons across facilities; ✓ corp manager views with aggregation | Present corp-level dashboard comparing facility queues and updated SPP⁺ with depth sensitivity. |

Exit checklist:
- [ ] Definition of Done satisfied (tests, docs, migrations, perf budgets).
- [ ] CHANGELOG.md updated per PR with perf note when hot paths touched.
- [ ] Constitution Update Checklist executed before altering guardrails.
