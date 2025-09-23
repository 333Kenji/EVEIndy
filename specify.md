# Overview
EVEINDY is an operations agent for EVE Online industrialists. It tracks corp-and-alt inventories, industry jobs, and market signals so it can recommend profitable manufacturing runs and keep valuations accurate.

# Problem Statement
- Current tooling treats production as stateless spreadsheets and cannot reconcile material reservations, in-flight jobs, and excess outputs.
- Rolling-average valuation data is hard to maintain; most calculators fall back to snapshot prices, causing distorted profitability reporting.
- Market advice rarely accounts for lead times, shallow depth, and demand depletion, so sell probability projections are unreliable.
- Planner workflows seldom respect the interplay between per-character slots, structure bonuses, and integer batch constraints.

# Users & Goals
- **Industrialist managing multiple characters** wants deterministic costing, job visibility, and planning support tied to live inventory.
- **Corporation production manager** wants to coordinate corp-level holdings, jobs, and market forecasts before assigning work.
- Goals:
  - Keep On-hand, At Jita, and Open Buy Orders buckets synchronized with rolling-average costs.
  - Make job costs, excess capitalization, and fee allocation transparent per run.
  - Expose market depth/volatility indicators and SPP⁺ forecasts that are aware of production lead times.
  - Recommend batch mixes and character/facility assignments that respect reservations, slots, and schedule windows.

# Current Capabilities
## Inventory & Ledger
- `/inventory/valuation` returns rolling-average quantities and costs from `inventory` for a requested owner scope, optionally filtered by type IDs. The service clamps consumption to available inventory and keeps valuations immutable except on acquisitions.【F:app/api/routes/inventory.py†L1-L18】【F:app/services/inventory.py†L1-L47】
- `/inventory/wip` aggregates outstanding outputs from queued/active jobs using the `industry_jobs` table so planners can factor committed production.【F:app/api/routes/inventory.py†L20-L24】【F:app/services/inventory.py†L49-L68】

## Bill of Materials & Costing
- `/bom/search` and `/bom/tree` expose blueprint metadata hydrated from SDE subset tables to power selection and BOM exploration; recursion depth is capped to prevent runaway traversal.【F:app/api/routes/bom.py†L1-L23】【F:app/services/bom.py†L1-L54】
- `/bom/cost` executes a consume-only costing pass that mixes rolling-average on-hand valuation with live mid-price fills when inventory is insufficient. Excess outputs and ME adjustments are handled in the math layer before totals are returned.【F:app/api/routes/bom.py†L25-L49】【F:app/services/costing_service.py†L1-L109】
- `indy_math.costing.cost_item` is the deterministic primitive used by higher-level costing flows. It recursively walks recipes, enforces integer runs, capitalizes excess outputs back into inventory, and tracks fee allocations via immutable traces.【F:indy_math/costing.py†L1-L170】

## Market Intelligence
- `/analytics/indicators` produces moving averages, Bollinger bands, volatility, and shallow depth metrics sourced from `orderbook_snapshots`; results are cached in Redis with last-good fallbacks.【F:app/api/routes/analytics.py†L1-L20】【F:app/services/analytics.py†L1-L108】
- `/analytics/spp_plus` evaluates sell probability with lead-time-aware depth forecasts and price policy inputs. Cached responses reuse deterministic forecasts while surfacing diagnostics for the UI.【F:app/api/routes/analytics.py†L22-L37】【F:app/services/analytics.py†L110-L170】
- `/prices/quotes` and `/prices/history` expose latest market quotes and historical mid/bid/ask series for dashboards and costing. Midpoints are derived from the most recent bid/ask pair per type and region.【F:app/api/routes/prices.py†L1-L52】

## Planning & Scheduling
- `/plan/next-window` and `/plan/recommend` wrap `indy_math.planner` to generate per-character schedules and assignments. Input parsing enforces slot declarations, per-run durations, and facility bonuses before calling the math core.【F:app/api/routes/plan.py†L1-L24】【F:app/services/plan.py†L1-L156】
- The planner computes deterministic assignments, schedules batches across slots, and surfaces overflow/unassigned work so operators can react before a refactor expands capabilities.【F:indy_math/planner.py†L1-L120】

## UI State & Reference Data
- `/state/ui` persists layout preferences in the `ui_state` table via UPSERT with automatic timestamp updates so the React client can restore panes per user profile.【F:app/api/routes/ui_state.py†L1-L26】【F:migrations/versions/20240416_04_ui_state.py†L1-L95】
- `/systems` serves cached system/constellation/region metadata plus industry indices, using Redis-backed caching for repeated lookups. `/structures/rigs` returns rig modifiers with static fallbacks if the subset tables are empty.【F:app/api/routes/systems.py†L1-L18】【F:app/services/systems.py†L1-L82】【F:app/api/routes/structures.py†L1-L40】
- `/metrics` exposes rate limiter counters for operational dashboards, reflecting guardrails enforced at the provider adapter layer.【F:app/api/routes/metrics.py†L1-L10】【F:app/rate_limit.py†L1-L45】

# External Data & Integrations
- **ESI**: `app.providers.esi` and `app.workers.esi_sync` fetch industry jobs and reconcile reservations. Jobs are mapped through repository protocols so idempotent updates can be tested without a live database.【F:app/workers/esi_sync.py†L1-L47】
- **Price Providers**: Adam4EVE and Fuzzwork adapters implement a common factory contract and are rate-limited through `core.ratelimiter.RateLimiter` configured per provider.【F:app/providers/factory.py†L1-L92】【F:core/ratelimiter.py†L1-L87】
- **SDE ingestion**: `utils/fetch_and_load_sde.py`, `utils/load_sde_dir.py`, and `utils/manage_sde.py` manage downloads, checksum validation, and subset loading. `app.sde_autoload.schedule_autoload` watches `data/SDE/_downloads` every six hours and calls the loader when new drops are detected, maintaining a manifest checksum.【F:app/sde_autoload.py†L1-L105】【F:utils/fetch_and_load_sde.py†L1-L200】
- **Celery tasks**: `tasks.price_refresh` polls configured providers, persists snapshots, and feeds charts; indicator recompute stubs are scheduled for hourly runs. Task cadence is defined in `app/schedules.py` and respects constitution guardrails.【F:tasks.py†L1-L55】【F:app/schedules.py†L1-L13】

# Technical Architecture
## Backend Layout
- FastAPI application (`app/main.py`) wires routers, applies CORS for the Vite dev server, and primes settings on startup. APScheduler kicks off SDE autoload without blocking startup.【F:app/main.py†L1-L36】
- Routers under `app/api/routes` dispatch to service modules that encapsulate DB/Redis access. Services construct SQLAlchemy engines on demand using configuration from `app.config.Settings`.
- Celery workers (`celery_app.py`, `tasks.py`) share settings with the API and use SQLAlchemy engines within managed transactions for deterministic DB writes.【F:celery_app.py†L1-L60】

## Math Core Modules
- `indy_math.costing` handles consume-only costing, recursion, and excess capitalization.
- `indy_math.indicators` & `app.services.analytics` cooperate to compute moving averages, Bollinger bands, volatility, and depth metrics for cached analytics.
- `indy_math.spp` implements the sell-probability calculation with deterministic random-free forecasts. Planner math lives in `indy_math.planner` as a pure scheduling engine.

## Persistence Model
- Core industry tables (`inventory`, `inventory_by_loc`, `acquisitions`, `consumptions`, `industry_jobs`, `buy_orders`, `orderbook_snapshots`, `consumption_log`) are established via Alembic migrations with deterministic enum types and timestamp triggers.【F:migrations/versions/20240416_01_initial_schema.py†L1-L170】
- SDE subset migrations add `type_ids`, `blueprints`, `rigs`, `structures`, `cost_indices`, and related lookup tables needed by BOM, systems, and structure APIs.【F:migrations/versions/20240416_02_sde_schema.py†L1-L200】【F:migrations/versions/20240416_03_subset_schema.py†L1-L160】
- `market_snapshots` supplements `orderbook_snapshots` so price history APIs can read pre-aggregated series without scanning raw order books.【F:migrations/versions/20240416_05_industry_materials.py†L1-L120】【F:tasks.py†L32-L55】
- `ui_state` stores serialized layout preferences with automatic `updated_at` maintenance for optimistic concurrency.【F:migrations/versions/20240416_04_ui_state.py†L1-L95】

## Caching & Rate Limiting
- `app.cache.CacheClient` provides structured TTL policies per domain (price, index, indicator, SPP) and maintains `:last_good` fallbacks for resilience. Age/staleness metadata is returned to callers to drive UI freshness indicators.【F:app/cache.py†L1-L87】
- `app.services.systems` and analytics modules read/write caches using safe helpers that swallow Redis outages to preserve determinism.【F:app/services/systems.py†L1-L82】【F:app/services/analytics.py†L33-L108】
- Provider requests obtain `RateLimiter` instances via `app.rate_limit.limiter_for_provider`, ensuring capacity/refill rates are centrally configured and metrics surfaced under `/metrics`.【F:app/rate_limit.py†L1-L49】

# API Surface
| Endpoint | Method | Summary |
| --- | --- | --- |
| `/health/live` `/health/ready` `/health/startup` | GET | Probe endpoints used by infra and tests.【F:app/main.py†L24-L44】 |
| `/inventory/valuation` | GET | Rolling-average inventory snapshot per owner scope.【F:app/api/routes/inventory.py†L1-L18】 |
| `/inventory/wip` | GET | Outstanding production quantities derived from ESI sync data.【F:app/api/routes/inventory.py†L20-L24】 |
| `/bom/search` | GET | Lookup products/blueprints by name for selection workflows.【F:app/api/routes/bom.py†L1-L14】 |
| `/bom/tree` | GET | Material tree expansion with bounded recursion.【F:app/api/routes/bom.py†L16-L24】 |
| `/bom/cost` | POST | Consume-only costing with ME bonus and optional owner-scope valuation.【F:app/api/routes/bom.py†L25-L49】 |
| `/analytics/indicators` | GET | Moving average, Bollinger, volatility, depth metrics per type/region.【F:app/api/routes/analytics.py†L1-L20】 |
| `/analytics/spp_plus` | POST | Lead-time-aware sell probability with diagnostics and caching.【F:app/api/routes/analytics.py†L22-L37】 |
| `/prices/quotes` | POST | Latest mid/bid/ask snapshots for requested types.【F:app/api/routes/prices.py†L1-L33】 |
| `/prices/history` | GET | Recent quote series for charting.【F:app/api/routes/prices.py†L35-L52】 |
| `/plan/next-window` `/plan/recommend` | POST | Planner scheduling and assignment recommendations.【F:app/api/routes/plan.py†L1-L24】 |
| `/systems` | GET | Cached system/constellation/region + cost index lookup.【F:app/api/routes/systems.py†L1-L18】 |
| `/structures/rigs` | GET | Rig modifiers filtered by activity with DB fallback to curated defaults.【F:app/api/routes/structures.py†L1-L40】 |
| `/state/ui` | GET/POST | Persisted UI layout state per identifier.【F:app/api/routes/ui_state.py†L1-L26】 |
| `/metrics` | GET | Rate limiter counters for observability.【F:app/api/routes/metrics.py†L1-L10】 |

# Background Jobs & Scheduling
- APScheduler launches SDE autoload scans every six hours to detect new drops in the offline staging directory.【F:app/sde_autoload.py†L77-L105】
- Celery Beat (or APScheduler integration) executes the cadence defined in `app/schedules.SCHEDULE`, covering price refresh, ESI sync, assets sync, indicator recompute, and alerts; tasks must remain idempotent and tolerate cache/provider outages.【F:app/schedules.py†L1-L13】
- Celery tasks call provider factories with rate-limited HTTP clients and persist snapshots plus derived metrics in a single DB transaction to avoid partial writes.【F:tasks.py†L1-L55】

# Non-Functional Requirements
- Deterministic math: all `indy_math` modules avoid side effects and accept explicit contexts so costing, SPP⁺, and planning remain replayable.【F:indy_math/costing.py†L1-L170】【F:indy_math/planner.py†L1-L120】
- Latency targets: cached read endpoints (inventory, indicators, systems) should respond within 150 ms P95 by using Redis or pre-aggregated tables.【F:app/cache.py†L1-L87】
- Reliability: provider adapters honour rate limits and provide circuit-breaker-friendly metrics. Cache envelopes include freshness metadata for UI warnings on stale data.【F:app/rate_limit.py†L1-L49】【F:app/cache.py†L61-L87】
- Security: secrets and tokens are injected via environment variables; UI state and audit tables carry timestamps for traceability.【F:celery_app.py†L1-L60】【F:migrations/versions/20240416_04_ui_state.py†L1-L95】

# Testing & Validation Expectations
- Math core modules require golden fixtures and determinism tests (property tests for planner/indicators) before GA.
- Provider adapters should be validated with recorded HTTP fixtures that cover success, failure, and throttled responses.
- API routes must have pytest/httpx coverage for success, validation errors, and cache fallbacks. Planner, costing, and BOM flows need integration tests against seeded schema snapshots.

# Refactor Readiness
- Centralize SQLAlchemy engine/session management to avoid ad-hoc engine creation per service and simplify transaction scoping.
- Replace direct `_get_value`/`_set_value` cache calls in services with dedicated helper methods to encapsulate envelope logic and error handling.
- Formalize repository implementations under `app.repos.pg_*` to decouple service logic from inline SQL and enable easier swapping during refactors.
- Expand Celery tasks beyond placeholders, ensuring indicator recompute and alerting operate from declarative task configs before the upcoming refactor.
- Harden planner and costing APIs with validation schemas (Pydantic models) to prepare for contract-first refactors and typed frontend clients.
