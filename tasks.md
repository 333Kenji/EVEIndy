Format:
- [ ] TASK: <title> (id: T-####)
Why: <1–2 line rationale>
Deliverables: <files / endpoints / artifacts>
Acceptance:
  - <verifiable check>
Depends on: T-####, …
Estimate: S/M/L (S≦2h, M≦1d, L≦3d)
Owner: (unset)
DoD (global): tests passing, docs updated, no schema drift, lint/format clean.
Tags: [core] [api] [db] [math] [adapter] [ui] [ops] [tests]

# Sprint 0 — Project Bootstrap

- [ ] TASK: Bootstrap IndyCalculator Environment (id: T-0001)
Why: Establish the mandated Python venv, dependency pins, and local tooling baseline.
Deliverables: requirements.txt, docs/setup.md, .env.example, pyproject.toml or ruff/black config files.
Acceptance:
  - `docs/setup.md` documents creating the `IndyCalculator` venv, installing pinned requirements, and running `uvicorn app.main:app --reload`.
  - requirements.txt includes pinned versions for FastAPI, SQLAlchemy, Celery, Redis-py, Pandas, NumPy, statsmodels, httpx, tenacity, pytest, black, ruff.
  - `.env.example` lists required env vars (ESI client creds, Postgres DSN, Redis URL) without secrets.
  - Lint/format configs reference the `IndyCalculator` interpreter path.
Estimate: M
Owner: (unset)
Tags: [core] [ops]

- [ ] TASK: Scaffold FastAPI Service Skeleton (id: T-0002)
Why: Provide the service boundary that separates stateful orchestration from the stateless math core.
Deliverables: app/main.py, app/api/__init__.py, app/dependencies.py, app/math/__init__.py, app/config.py, tests/api/test_health.py.
Acceptance:
  - FastAPI app exposes `/health/live`, `/health/ready`, `/health/startup` returning the expected status codes.
  - `app/math` package exports placeholder pure functions with no external imports beyond stdlib/typing.
  - `tests/api/test_health.py` passes via `pytest` in the IndyCalculator venv.
Depends on: T-0001
Estimate: M
Owner: (unset)
Tags: [core] [api] [math]

- [ ] TASK: Establish Postgres Schema & Alembic Migrations (id: T-0003)
Why: Create the durable data model required for rolling averages, reservations, and auditability.
Deliverables: alembic.ini, migrations/env.py, migrations/versions/*_initial_schema.py, docs/schema.md.
Acceptance:
  - Initial migration creates tables `inventory`, `inventory_by_loc`, `acquisitions`, `consumptions`, `industry_jobs`, `buy_orders`, `orderbook_snapshots`, `consumption_log` with keys/indexes per plan.
  - Monetary columns use `NUMERIC(28,4)` and quantity columns use `NUMERIC(20,2)`.
  - Migration adds `inventory_coverage_view` view aggregating location buckets.
  - `alembic upgrade head` runs cleanly against a fresh Postgres container.
Depends on: T-0001, T-0002
Estimate: L
Owner: (unset)
Tags: [db] [ops]

- [ ] TASK: Implement Math Core Primitives with Determinism Tests (id: T-0004)
Why: Encode consume-only costing and lead-time–aware SPP⁺ as pure, testable functions.
Deliverables: indy_math/costing.py, indy_math/spp.py, indy_math/indicators.py, tests/math/test_costing.py, tests/math/test_spp.py, tests/math/test_indicators.py.
Acceptance:
  - `cost_item` handles on-hand consumption, recursive make steps, excess capitalization, and fee pro-rating exactly as described in the constitution.
  - `spp_lead_time_aware` returns identical outputs for repeated runs with identical inputs; tests include zero-depth and high-depth edge cases.
  - Indicator utilities compute moving averages, Bollinger bands, and depth summaries with validation on insufficient data.
  - Math tests achieve 100% coverage of ISK-affecting code paths and run without touching network/DB.
Depends on: T-0002
Estimate: L
Owner: (unset)
Tags: [math] [tests]

- [ ] TASK: Build Provider Adapter Interfaces with Retry/Backoff (id: T-0005)
Why: Encapsulate ESI and price providers with guardrails for cache windows, rate limits, and failover.
Deliverables: app/providers/base.py, app/providers/esi.py, app/providers/adam4eve.py, app/providers/fuzzwork.py, tests/providers/test_contracts.py, docs/providers.md.
Acceptance:
  - Adapters expose typed interfaces matching the plan (jobs, assets, skills, cost indices, price quotes).
  - Exponential backoff with full jitter is applied; exceeding retry threshold raises a circuit-breaker exception.
  - Adapter responses are validated against Pydantic models and reject schema drift.
  - Contract tests use recorded fixtures (no live calls) and simulate rate-limit and failure scenarios.
Depends on: T-0002
Estimate: L
Owner: (unset)
Tags: [adapter] [core] [tests]

- [ ] TASK: Configure Redis Caching & Settings (id: T-0006)
Why: Enforce the required TTLs, last-good fallbacks, and cache-aside strategy for hot paths.
Deliverables: app/cache.py, app/settings.py updates, redis/keys.md, tests/cache/test_cache_policy.py.
Acceptance:
  - Redis helper supports namespaced keys (`price:{provider}:{region}:{type}`, etc.) with TTLs 900s/86400s/3600s/1800s per plan.
  - Cache layer returns last-good values when providers fail and tags staleness metadata for API responses.
  - Tests cover expiry behaviour and last-good fallback, using fakeredis or Redis test container.
  - Settings surface Redis URL via environment variable and integrate with FastAPI dependency wiring.
Depends on: T-0002
Estimate: M
Owner: (unset)
Tags: [core] [ops] [tests]

- [ ] TASK: Implement Inventory & Job Sync Workers (id: T-0007)
Why: Keep stateful reservations and rolling averages aligned with ESI data and acquisitions.
Deliverables: app/workers/__init__.py, app/workers/esi_sync.py, tests/workers/test_esi_sync.py, docs/workflows/esi_sync.md.
Acceptance:
  - Worker pulls ESI jobs/assets respecting cache headers and upserts into Postgres with `SELECT ... FOR UPDATE` to maintain reservations.
  - Excess outputs generate acquisition records with proper unit costs and update rolling averages atomically.
  - Tests simulate new jobs, completed jobs, and cancellations ensuring idempotent updates.
  - Documentation outlines manual re-sync procedure and rate-limit safeguards.
Depends on: T-0003, T-0005, T-0006
Estimate: L
Owner: (unset)
Tags: [core] [db] [adapter] [ops] [tests]

- [ ] TASK: Expose Analytics & Planning APIs (id: T-0008)
Why: Deliver the endpoints that drive SPP⁺, indicators, and planning workflows for the UI.
Deliverables: app/api/routes/analytics.py, app/api/routes/plan.py, schemas/analytics.py, tests/api/test_analytics.py, tests/api/test_plan.py.
Acceptance:
  - `/analytics/indicators` returns cached MA/BB/volatility data with 200/429/503 handling per plan.
  - `/analytics/spp_plus` consumes math core outputs, honors deterministic behaviour, and surfaces diagnostics.
  - `/plan/next-window` produces per-character recommendations while enforcing integer batch constraints and conflict checks.
  - API tests cover happy path, validation errors, and provider outage fallbacks.
Depends on: T-0004, T-0005, T-0006, T-0007
Estimate: L
Owner: (unset)
Tags: [api] [math] [core] [tests]

- [ ] TASK: Wire Celery/APScheduler Schedules (id: T-0009)
Why: Ensure recurring jobs honor cadences and idempotency constraints defined in the plan.
Deliverables: celery_app.py, app/schedules.py, docs/ops/schedules.md, tests/ops/test_schedules.py.
Acceptance:
  - Celery app registers queues for price refresh, indices, ESI sync, indicators, and Discord alerts with staggering and TTL guards.
  - APScheduler configuration seeds the 12-minute price refresh, daily indices, 30-minute job sync, hourly indicators, and 15-minute alerts.
  - Tests verify schedule definitions and idempotent task wrappers (mocked Celery beat context).
  - Documentation includes runbooks for retry storms and manual task triggering.
Depends on: T-0005, T-0006, T-0007
Estimate: M
Owner: (unset)
Tags: [ops] [core]

- [ ] TASK: Scaffold React Dashboard Shell (id: T-0010)
Why: Provide UI entry points for coverage bars, SPP⁺ controls, and planning views.
Deliverables: frontend/package.json, frontend/src/App.tsx, frontend/src/pages/Dashboard.tsx, frontend/src/api/client.ts, frontend/src/components/CoverageBars.tsx, tests/ui/Dashboard.test.tsx.
Acceptance:
  - React app bootstraps via Vite with TypeScript and TanStack Query configured.
  - Dashboard fetches `/state/ui` (mocked) and renders coverage bars using placeholder data bindings.
  - SPP⁺ controls component wires to `/analytics/spp_plus` stub with explainable cost trace panel ready for integration.
  - UI tests (React Testing Library) validate coverage bar rendering and API hook error states.
Depends on: T-0002, T-0008
Estimate: M
Owner: (unset)
Tags: [ui] [api] [tests]

- [ ] TASK: Establish CI Pipeline & Quality Gates (id: T-0011)
Why: Enforce constitution-mandated tests, lint, and determinism checks on every PR.
Deliverables: .github/workflows/ci.yml, scripts/run_tests.sh, scripts/lint.sh, docs/process/ci.md.
Acceptance:
  - CI workflow runs lint (`ruff`), format check (`black --check`), unit/integration tests (`pytest`), and coverage with ≥85% threshold enforcement.
  - Pipeline includes deterministic math test job that executes relevant suites twice to confirm repeatability.
  - Workflow uploads coverage artifact and fails on schema drift by verifying `alembic heads` equals `alembic current`.
  - Documentation states PR requirements (tests, CHANGELOG entry, performance note when hot paths touched).
Depends on: T-0001, T-0004, T-0005, T-0006
Estimate: M
Owner: (unset)
Tags: [ops] [tests]
