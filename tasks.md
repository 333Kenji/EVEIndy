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

- [ ] TASK: One-shot SDE Folder Loader (id: T-0034)
Why: Make SDE imports effortless by pointing at extracted SDE directory.
Deliverables: utils/load_sde_dir.py and tests/utils/test_load_sde_dir.py.
Acceptance:
  - Running `python utils/load_sde_dir.py /path/to/sde` discovers typeIDs.yaml and industryBlueprints.yaml and runs importer in correct order.
  - `--no-db` supported to skip upserts.
Estimate: S
Owner: (unset)
Tags: [db] [ops]

# Sprint 3 — SDE Auto-Download & UX polish

- [ ] TASK: SDE Auto-Downloader + Loader CLI (id: T-0035)
Why: One-command tool that fetches the latest CCP SDE, decompresses, parses, and upserts into Postgres.
Deliverables: utils/fetch_and_load_sde.py (CLI), docs/sde_auto.md, tests/utils/test_fetch_and_load_sde.py (offline fixtures).
Acceptance:
  - Running `python utils/fetch_and_load_sde.py` discovers the latest version from https://developers.eveonline.com/static-data, downloads typeIDs + industryBlueprints archives, verifies checksums (when available), decompresses, and invokes manage_sde.update in the correct order.
  - Supports flags: `--version vYYYY.MM.DD`, `--dir <path>` for temp/output, `--no-db` to skip upserts, `--force` to re-download.
  - Resilient networking: retries with backoff + jitter, progress output, resumes partial downloads when possible.
Estimate: M
Owner: (unset)
Tags: [ops]

- [ ] TASK: SDE Downloader Networking + Proxy Support (id: T-0036)
Why: Ensure reliable downloads in corporate/proxy environments.
Deliverables: downloader honors `HTTP_PROXY`/`HTTPS_PROXY` envs, configurable timeout, retry policy; tests with mocked HTTP.
Acceptance:
  - Downloader uses proxies when env vars present; fails gracefully with actionable error when unreachable.
  - Unit tests cover success, 404, and retry scenarios using recorded fixtures.
Estimate: S
Owner: (unset)
Tags: [ops] [tests]

- [ ] TASK: SDE Integrity & Attribution (id: T-0037)
Why: Ensure integrity and proper attribution for redistributed subsets.
Deliverables: checksum verification logic (sha256/sha1 when published), docs/ATTRIBUTION.md with CCP SDE notice, version manifest persisted.
Acceptance:
  - Loader rejects mismatched checksums unless `--force` is provided.
  - Attribution doc exists and version manifest updated per import.
Estimate: S
Owner: (unset)
Tags: [ops] [docs]

- [ ] TASK: README Quickstart (SDE + Frontend) (id: T-0038)
Why: Provide a short path for new contributors without Docker.
Deliverables: README section with commands: create venv, install reqs, run Postgres, `fetch_and_load_sde.py`, alembic upgrade, uvicorn, and Vite dev.
Acceptance:
  - Steps copy-paste cleanly on a fresh machine and result in a working UI with live prices and loaded SDE subsets.
Estimate: S
Owner: (unset)
Tags: [docs]

# Sprint 4 — Local SDE Ingest + Calculator/BOM UX

- [ ] TASK: SDE Local Loader (load-local CLI) (id: T-0039)
Why: Allow manual local SDE refresh without network; load from `data/SDE/_downloads/` and (re)populate DB subset.
Deliverables: `utils/manage_sde.py load-local` command, logs and summary.
Acceptance:
  - Validates presence of YAML or JSON (prefers YAML) under `data/SDE/_downloads/`.
  - Parses subset only: T2 frigates/cruisers blueprints/products; reactions (moongoo→advanced mats→components); structures (Raitaru, Tatara, Athanor, Azbel), rigs, service modules; IDs (system/region/constellation).
  - Idempotent upsert; summary counts + version/hash printed.
Depends on: T-0015, T-0030
Estimate: M
Owner: (unset)
Tags: [db] [ops]

- [ ] TASK: SDE Subset Schema Extensions (id: T-0040)
Why: Persist required subsets not covered by existing tables.
Deliverables: Alembic migration(s) for `structures` enrichments, `rigs`, `services`, `universe_ids` (system/region/constellation), and reaction links if needed.
Acceptance:
  - Tables created with PK/FK indexes; upserts supported.
  - Migrations run cleanly on empty DB.
Depends on: T-0003
Estimate: M
Owner: (unset)
Tags: [db]

- [ ] TASK: SDE Local Loader Tests (id: T-0041)
Why: Validate parsing + upsert using tiny fixture files.
Deliverables: fixtures under `tests/fixtures/sde/`, tests for `load-local` happy path and idempotency.
Acceptance:
  - First run inserts subset rows; second run produces no duplicates.
Depends on: T-0039, T-0040
Estimate: S
Owner: (unset)
Tags: [tests]

- [ ] TASK: Docs — Local-Only SDE Workflow (id: T-0042)
Why: Document manual refresh procedure for contributors.
Deliverables: README + plan.md updates describing `load-local`, required files/paths, and subset scope.
Acceptance:
  - Copy-paste steps produce a refreshed subset DB on a clean repo.
Depends on: T-0039
Estimate: S
Owner: (unset)
Tags: [docs]

- [ ] TASK: Calculator Selectors & Presets (id: T-0043)
Why: Provide UI controls for ship class/size, structures, rigs, skills with sensible defaults.
Deliverables: React controls (toggles/dropdowns), default state pre-seeded (dummy char @5, Tatara+T1 rigs, Raitaru ME rigs, Nitrogen Fuel Blocks sample).
Acceptance:
  - Changing selectors updates displayed materials and job time immediately.
Depends on: T-0020, T-0021
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Rolling-Average Valuation for On-Hand (id: T-0077)
Why: Use rolling-average costs for all on-hand inventory; eliminate snapshot pricing for holdings.
Deliverables: inventory valuation service using `acquisitions/consumptions` ledgers; endpoints to return valued on-hand by `type_id`.
Acceptance:
  - Given acquisition and consumption events, service returns correct rolling-average and quantity; determinism tests cover edge cases.
Depends on: T-0003 (schema), T-0004 (math), T-0007 (ESI sync)
Estimate: M
Owner: (unset)
Tags: [db] [math] [api] [tests]

- [ ] TASK: Live WIP/Jobs Tracking from ESI (id: T-0078)
Why: Count “in production” items correctly in coverage/needs and planning.
Deliverables: ESI sync extension to compute WIP outputs per job (by product `type_id`, remaining runs, output_qty) and expose `/inventory/wip`.
Acceptance:
  - WIP reflects ESI queued/active jobs; delivered jobs decrement WIP and increment on-hand; idempotent updates.
Depends on: T-0005 (ESI), T-0007 (workers)
Estimate: M
Owner: (unset)
Tags: [adapter] [db] [api]

- [ ] TASK: Weekly Run Planner (Global Cutoff + Staggered Starts) (id: T-0079)
Why: Plan runs over a 7‑day window with a global cutoff and staggered job starts across characters.
Deliverables: planning service that accepts cutoff + roster and returns per-character run schedule (start time, job, runs) honoring slots and integer batches.
Acceptance:
  - Planner output respects slots, cutoff, integer batches; unit tests validate schedules across sample rosters.
Depends on: T-0078 (WIP), T-0077 (valuation)
Estimate: L
Owner: (unset)
Tags: [math] [api] [tests]

- [ ] TASK: Builder Recommender (Assign Jobs by Skills/Bonuses/Slots) (id: T-0080)
Why: Choose best character + facility for each job based on skills, structure bonuses, and available slots.
Deliverables: recommender that scores assignments and outputs a per-character queue; API endpoint `/plan/recommend`.
Acceptance:
  - Recommender assigns jobs deterministically given fixed inputs; tests cover skill/rig variations and slot limits.
Depends on: T-0066 (structures/roles), T-0079 (planner)
Estimate: L
Owner: (unset)
Tags: [math] [api] [tests]

- [ ] TASK: UI — Character Order & Weekly Needs vs On‑Hand+WIP (id: T-0081)
Why: Let users order characters and visualize weekly needs versus on-hand and WIP.
Deliverables: UI controls to order characters; stacked bars for needs vs on-hand and WIP; binds to planner + valuation endpoints.
Acceptance:
  - Changing character order reflows schedules; chart shows needs reduced by on-hand/WIP; state persists.
Depends on: T-0077, T-0078, T-0079
Estimate: M
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Costing Policy Enforcement (RA for holdings; Spot for shortfalls) (id: T-0082)
Why: Enforce policy: rolling-average for on-hand; snapshot/spot only for deficits.
Deliverables: costing service update to separate on-hand valuation (RA) from shortfall priced via quotes; docs section in plan.md.
Acceptance:
  - Cost outputs use RA for on-hand and spot (with timestamp) for deficits; tests verify mixed scenarios.
Depends on: T-0077, T-0017 (quotes)
Estimate: M
Owner: (unset)
Tags: [math] [api] [docs] [tests]

- [ ] TASK: UI — Item Filter Preview (id: T-0083)
Why: Let users scope inventory/products from the UI before committing to calculations or exports.
Deliverables: React filter panel with selectors backed by DB metadata (category, group, meta level, blueprint/inventory flags); TanStack Query hook and API client for `/items/preview`; FastAPI endpoint + service method translating filters into SQL against `type_ids`/inventory tables; Vitest + API tests covering filter combinations.
Acceptance:
  - Changing any selector updates the request payload and clicking "Preview Item List" fetches filtered results from the database and renders name/type/quantity rows.
  - All filter controls derive their option lists from live DB values rather than hard-coded enums.
  - Preview endpoint enforces filter predicates (category, group, meta, blueprint/inventory) in generated SQL and returns only matching rows; tests assert representative combinations.
Depends on: T-0008 (API surface), T-0039, T-0040 (type_ids + inventory schema)
Estimate: M
Owner: (unset)
Tags: [ui] [api] [db] [tests]
- [ ] TASK: Calculator Math Wiring to Endpoints (id: T-0044)
Why: Ensure live math reflects UI changes.
Deliverables: Frontend calls to backend math endpoints where applicable; fallback to pure functions for local interactions.
Acceptance:
  - Materials/time recompute deterministically on skill/rig/structure changes; network errors fall back gracefully.
Depends on: T-0008, T-0020
Estimate: M
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Calculator UI Tests (id: T-0045)
Why: Guard against regressions.
Deliverables: Vitest/RTL tests for selectors affecting outputs; snapshot for default preset.
Acceptance:
  - Toggling skills/rigs/structures changes totals deterministically in tests.
Depends on: T-0043
Estimate: S
Owner: (unset)
Tags: [ui] [tests]

- [ ] TASK: T2 BOM Selector & Tree View (id: T-0046)
Why: Allow selecting any T2 frigate/cruiser and view its full BOM tree.
Deliverables: Searchable selector (DB-backed) and BOM tree component.
Acceptance:
  - Selecting a hull renders materials/components/reactions tree from SDE subset.
Depends on: T-0039, T-0040
Estimate: M
Owner: (unset)
Tags: [ui] [db]

- [ ] TASK: BOM Costing & Rolling Average (id: T-0047)
Why: Show costs using consume-only costing and rolling averages.
Deliverables: Backend endpoint/service to compute BOM costs; UI display components.
Acceptance:
  - Costs match deterministically for fixed inputs; excess capitalization respected.
Depends on: T-0004, T-0046
Estimate: M
Owner: (unset)
Tags: [math] [api] [ui]

- [ ] TASK: BOM Stability Tests (id: T-0048)
Why: Ensure numbers are stable for known hulls.
Deliverables: Unit/integration tests with seeded data for a known T2 hull.
Acceptance:
  - BOM and cost totals assert exact values with fixed fixtures.
Depends on: T-0047
Estimate: S
Owner: (unset)
Tags: [tests]

- [ ] TASK: Market Snapshots Table & Ingest Job (id: T-0049)
Why: Store periodic price/depth snapshots for charts.
Deliverables: Migration for `market_snapshots` (or reuse `orderbook_snapshots`), worker ingest job with polite cadence.
Acceptance:
  - Job writes rows on schedule; respects RateLimiter.
Depends on: T-0005, T-0012
Estimate: M
Owner: (unset)
Tags: [db] [ops] [adapter]

- [ ] TASK: Snapshots Query API (id: T-0050)
Why: Serve recent history to the UI.
Deliverables: GET `/prices/history?type_id=&region_id=&days=`; tests.
Acceptance:
  - Returns recent series with timestamps; supports pagination/limit.
Depends on: T-0049
Estimate: S
Owner: (unset)
Tags: [api]

- [ ] TASK: Price History Mini Chart (id: T-0051)
Why: Visualize recent prices on the calculator page.
Deliverables: React mini chart (sparklines or simple line chart) bound to snapshots API.
Acceptance:
  - Chart renders from fixtures in dev and real API in prod.
Depends on: T-0050
Estimate: S
Owner: (unset)
Tags: [ui]

- [ ] TASK: Market Snapshots Tests (id: T-0052)
Why: Validate worker/API/chart end-to-end.
Deliverables: Worker job unit test with faked provider; API test; UI fixture test.
Acceptance:
  - Rows produced; API returns expected points; chart renders with fixture data.
Depends on: T-0049, T-0050, T-0051
Estimate: M
Owner: (unset)
Tags: [tests]

- [ ] TASK: Pane Manager (drag/resize/reflow) (id: T-0053)
Why: Provide draggable, resizable overlay panels.
Deliverables: Pane manager component with open/close/drag/resize/stack, responsive reflow.
Acceptance:
  - Multiple panes can open and share space sensibly; keyboard/mouse interactions work.
Depends on: T-0043
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Sidebar Pane Launcher (id: T-0084)
Why: Provide a persistent sidebar to open panes, with the selected pane occupying the main viewport.
Deliverables: Left-side navigation component with buttons; when a pane is active it fills the primary content area (existing cards collapse beneath).
Acceptance:
  - Clicking a sidebar item opens the pane full-width within the current viewport; closing returns to the main layout; state persists via `/state/ui`.
Depends on: T-0053
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Production Facilities Entry in Sidebar (id: T-0085)
Why: Move the Production Facilities (systems/structures) view into the new sidebar as the first menu option.
Deliverables: Sidebar item labelled “Production Facilities” that activates the Systems pane/content; existing page card removed.
Acceptance:
  - Opening “Production Facilities” via sidebar shows systems/structures UI in the pane area; closing hides it; layout follows the new pane system.
Depends on: T-0084, T-0064
Estimate: S
Owner: (unset)
Tags: [ui]

- [ ] TASK: Domain Panes (Structures, Analytics, Materials) (id: T-0054)
Why: Surface detailed controls and insights.
Deliverables: Three panes wired to existing endpoints and calculator state.
Acceptance:
  - Structures Config, Analytics (indicators/SPP⁺), and Materials (coverage) panes function and reflect current selection.
Depends on: T-0053, T-0008, T-0017
Estimate: M
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Pane State Persistence (id: T-0055)
Why: Restore pane layout on reload.
Deliverables: Backend persistence (e.g., `/ui/state`), frontend save/restore hooks.
Acceptance:
  - Reload restores open panes and sizes/positions.
Depends on: T-0053
Estimate: S
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Pane Interaction Tests (id: T-0056)
Why: Ensure deterministic drag/resize/stack behavior.
Deliverables: Component tests for pane manager interactions.
Acceptance:
  - Open/close/drag/resize pass in CI with stable outcomes.
Depends on: T-0053
Estimate: S
Owner: (unset)
Tags: [ui] [tests]

- [ ] TASK: Background Nodes Param Refactor (id: T-0057)
Why: Allow tuning density/velocity/filament amplitude/gradient.
Deliverables: Background component props and config hook.
Acceptance:
  - Defaults applied via config; values can be overridden by panes.
Depends on: —
Estimate: S
Owner: (unset)
Tags: [ui]

- [ ] TASK: Background Defaults (Blue→Purple, 2× density) (id: T-0058)
Why: Match EVE star map vibe.
Deliverables: Update defaults to blue→purple gradient, ~2× density, slightly faster motion.
Acceptance:
  - Visual review shows denser field and new gradient.
Depends on: T-0057
Estimate: S
Owner: (unset)
Tags: [ui]

- [ ] TASK: Background Visual Snapshot Test (id: T-0059)
Why: Detect regressions in visuals.
Deliverables: Lightweight screenshot/snapshot test of canvas params (mocked).
Acceptance:
  - Test confirms parameterization and default config applied.
Depends on: T-0057, T-0058
Estimate: S
Owner: (unset)
Tags: [tests]

- [ ] TASK: Cross-Cutting E2E Acceptance (id: T-0060)
Why: Verify integration: calculator reactivity, SDE ingest, snapshots rendering.
Deliverables: Scripted checklist or smoke tests that toggle skills/structures/rigs; run SDE load-local; render price chart for selected hull.
Acceptance:
  - All checks pass; provider snapshots respect rate limits.
Depends on: T-0039, T-0045, T-0052
Estimate: M
Owner: (unset)
Tags: [ops] [ui] [db]

- [ ] TASK: Auto SDE Detect & Load (id: T-0061)
Why: Eliminate manual CLI by watching `data/SDE/_downloads/` and auto-loading new SDE snapshots into the subset DB.
Deliverables: `app/sde_autoload.py` (finder + needs_update + load_if_new), API startup scheduler hook (APScheduler) to scan on boot and every 6h; tests with fixtures (zip and yaml).
Acceptance:
  - On startup, if a new SDE (YAML/JSON or supported ZIP) is present, loader parses subset and upserts idempotently.
  - Subsequent scans skip when manifest checksum matches; logs summary counts.
Depends on: T-0039, T-0040, T-0041
Estimate: M
Owner: (unset)
Tags: [ops] [db]

- [ ] TASK: Full Industry SDE Ingest (subset) (id: T-0062)
Why: Populate DB with all materials/components/minerals used along the T2 frigate/cruiser chain plus universe IDs.
Deliverables: manage_sde.load_local enhancements to compute `industry_materials` from blueprints, upsert all blueprints in subset, and upsert `universe_ids` from map YAMLs; migrations; endpoint to query materials.
Acceptance:
  - After dropping SDE into `data/SDE/_downloads`, autoload populates `type_ids`, `blueprints`, `industry_materials`, and `universe_ids`.
  - Idempotent upserts; summary counts logged.
Depends on: T-0039, T-0040, T-0061
Estimate: M
Owner: (unset)
Tags: [db] [ops] [api]

# Sprint 5 — Systems/Structures + Ship Basket UI

- [ ] TASK: EVE Uni UX Review + UI Plan (id: T-0063)
Why: Align frontend with EVE Uni industry flow (facilities→roles→rigs→jobs).
Deliverables: docs/ui/industry_plan.md summarizing patterns + UI wireframes.
Acceptance:
  - Doc lists screen sections and interactions; maps to tasks T-0064..T-0072.
Depends on: —
Estimate: S
Owner: (unset)
Tags: [docs] [ui]

- [ ] TASK: Systems Page — System Bars (id: T-0064)
Why: Visualize systems and their system cost indices as bars.
Deliverables: /systems route, bar component, API call.
Acceptance:
  - Lists systems with name + current cost index; expand-on-click area renders below bar.
  - Uses cached indices and respects rate/TTL per Constitution §9 and Spec §Constraints.
Depends on: T-0040 (universe_ids), T-0018 (caching)
Estimate: M
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Add System — Search + Select (id: T-0065)
Why: Add systems from DB to user’s facility list.
Deliverables: searchable selector (universe_ids), POST `/state/ui` persistence.
Acceptance:
  - Search returns systems; adding persists; reload restores the list.
Depends on: T-0064, T-0055
Estimate: S
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Structures + Roles (id: T-0066)
Why: Attach structures to a system and choose industry role (Manufacturing, Reactions, Refining, Science).
Deliverables: dropdowns for structure type + role; per‑role form placeholders.
Acceptance:
  - “+ Add Structure” opens controls; selection persists under system bar.
Depends on: T-0065, T-0040
Estimate: M
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Rigs Mapping + Persistence (id: T-0067)
Why: Offer role‑appropriate rig options and save them.
Deliverables: rig list (rigs table), selection UI, POST `/state/ui` updates.
Acceptance:
  - Rigs shown per structure/role; saved and restored on reload.
Depends on: T-0066, T-0040
Estimate: S
Owner: (unset)
Tags: [ui] [db]

- [ ] TASK: Systems API (id: T-0068)
Why: Serve systems + cost indices for UI.
Deliverables: GET `/systems` returns id/name/index; tests.
Acceptance:
  - Returns cached indices with <150ms P95; pagination supported.
  - Provider/resource access follows Constitution §3/§9 (cache windows, backoff/jitter).
Depends on: T-0040, T-0018
Estimate: S
Owner: (unset)
Tags: [api]

- [ ] TASK: Ship Search + Basket (id: T-0069)
Why: Add ships to a build basket.
Deliverables: search component; basket item UI; state persistence.
Acceptance:
  - Selecting a ship adds a bar; reload restores basket via `/state/ui` (Constitution §11 persistence UX).
Depends on: T-0046, T-0055
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Expandable BOM UI (id: T-0070)
Why: Expand/collapse reactions → components → raw materials.
Deliverables: tree component bound to `/bom/tree`.
Acceptance:
  - Expand/collapse works; performance acceptable on typical hulls.
Depends on: T-0046
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Market Metrics on Ship Bar (id: T-0071)
Why: Show mid/volume/spread for selected ship.
Deliverables: bind `/prices/history` + quote endpoint; mini chart.
Acceptance:
  - Chart renders; metrics update within 150ms P95 from cache.
Depends on: T-0050, T-0017, T-0018
Estimate: S
Owner: (unset)
Tags: [ui] [api]

- [ ] TASK: Grand Profit/Cost Summary (id: T-0072)
Why: Live summary of total build cost, projected sale, and profit.
Deliverables: summary bar component; combine basket items; fees/rigs/skills inputs.
Acceptance:
  - Updates deterministically on ship qty/rig/skill changes (Constitution §8 determinism tests).
Depends on: T-0069, T-0047
Estimate: M
Owner: (unset)
Tags: [ui] [math]

- [ ] TASK: Live Interaction Wiring (id: T-0073)
Why: Ensure changes propagate through math and state.
Deliverables: hooks to recompute materials/time on rig/structure/skill changes; debounce + caching.
Acceptance:
  - Inputs update BOM and summary within 200ms; state persists.
Depends on: T-0066, T-0067, T-0069, T-0072
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Visual Polish (icons + palette overlays) (id: T-0074)
Why: Improve legibility and brand fit.
Deliverables: ship icon overlay with palette gradients; hover/focus states.
Acceptance:
  - Bars show icons/gradients; passes contrast checks.
Depends on: T-0069
Estimate: S
Owner: (unset)
Tags: [ui]

- [ ] TASK: Populate Rigs from SDE Mapping (id: T-0075)
Why: Replace fallback rigs with real entries sourced from SDE/group mappings.
Deliverables: parser to identify rig items by group/category; upsert into `rigs`; role mapping table or rules.
Acceptance:
  - `/structures/rigs` returns DB-sourced rigs per role; fallback no longer used when DB populated.
Depends on: T-0039, T-0040
Estimate: M
Owner: (unset)
Tags: [db] [ops]

- [ ] TASK: Enhanced System Selector (id: T-0076)
Why: Improve usability when adding systems.
Deliverables: search with pagination, filter by region/constellation; keyboard navigation.
Acceptance:
  - Selector lists multiple results and supports arrow/enter; filters by region/constellation.
Depends on: T-0068
Estimate: S
Owner: (unset)
Tags: [ui]

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

- [ ] TASK: Implement Central RateLimiter and Integrate Providers (id: T-0012)
Why: Enforce per-provider rate limits and polite cadences, preventing ban/blocks.
Deliverables: core/ratelimiter.py, tests/core/test_ratelimiter.py, provider wiring updates.
Acceptance:
  - RateLimiter exposes token-bucket semantics with fakeable clock/sleep for tests.
  - Metrics counters (`allowed`, `denied`, `delayed`) increment as expected.
  - ESI/Adam4EVE/Fuzzwork adapters block until allowed before issuing requests.
  - Contract tests simulate limiter blocking via injected fake sleep/clock.
Estimate: M
Owner: (unset)
Tags: [adapter] [core] [tests]

- [ ] TASK: SDE Manager Utility + Schema (id: T-0013)
Why: Parse and store SDE subsets needed for T2 manufacturing workflows.
Deliverables: utils/manage_sde.py CLI, migrations/20240416_02_sde_schema.py, tests/utils/test_manage_sde.py, docs updates.
Acceptance:
  - CLI `python utils/manage_sde.py update --from-file <yaml>` updates `data/sde/` and writes a manifest with version+checksum.
  - Migration creates `type_ids`, `blueprints`, `structures`, `cost_indices` tables.
  - Unit tests verify manifest roundtrip and basic update no-op when checksum unchanged.
  - `.gitignore` excludes `data/sde/` artifacts.
Estimate: L
Owner: (unset)
Tags: [db] [ops] [tests]

- [ ] TASK: Provider Rate Limit Settings & Wiring (id: T-0014)
Why: Make provider-specific rate limits configurable via env and settings.
Deliverables: app/settings.py updates, wiring of RateLimiter instances in provider factories, docs snippet.
Acceptance:
  - Env vars define capacities/refill rates per provider (ESI, Adam4EVE, Fuzzwork), with sane defaults.
  - Providers receive a RateLimiter instance via DI and honor it in calls.
  - Unit test verifies env-driven settings produce expected limiter configuration.
Estimate: S
Owner: (unset)
Tags: [adapter] [core] [ops] [tests]

- [ ] TASK: SDE Parser for T2 Subsets + Idempotent Upserts (id: T-0015)
Why: Load actionable blueprint/material data for T2 frigates/cruisers and reactions.
Deliverables: utils/manage_sde.py parsing functions, db upsert script(s), tests for parsing subsets and idempotency.
Acceptance:
  - Parser extracts blueprints→products, reaction chains, and relevant structures into compact JSON.
  - Idempotent upsert inserts/updates `type_ids`, `blueprints`, `structures` in Postgres without duplicates.
  - Tests validate parsing of small YAML fixtures and repeatable upserts.
Estimate: L
Owner: (unset)
Tags: [db] [ops] [tests]

- [ ] TASK: Document SDE + Rate Limit Workflows (id: T-0016)
Why: Ensure developers follow proper offline SDE updates and safe provider usage.
Deliverables: plan.md additions, docs/sde.md, docs/rate_limits.md.
Acceptance:
  - plan.md describes local `manage_sde.py update` workflow; production images do not bundle raw SDE.
  - Rate-limit guardrails documented with examples of adding new provider keys and cadences.
  - Cross-link from README.
Estimate: S
Owner: (unset)
Tags: [ops] [docs]

# Sprint 1 — Live Data, Caching, UI

- [ ] TASK: Live Prices API from Snapshots (id: T-0017)
Why: Expose latest bid/ask/mid from `orderbook_snapshots` for UI calculators.
Deliverables: app/api/routes/prices.py, app/services/prices.py, tests/api/test_prices.py.
Acceptance:
  - POST `/prices/quotes` accepts `{ region_id, type_ids: [] }` and returns `{ quotes: [{type_id, bid, ask, mid, ts}] }`.
  - Endpoint queries latest per (type_id, side) by `ts` and computes mid.
  - Tests mock the service to avoid DB dependency.
Estimate: M
Owner: (unset)
Tags: [api] [db] [tests]

- [ ] TASK: Cache Analytics Outputs in Redis (id: T-0018)
Why: Reduce load and meet P95 latency targets for indicators/SPP⁺.
Deliverables: app/services/analytics.py updates using CacheClient, tests/cache for cache-hit logic.
Acceptance:
  - `/analytics/indicators` and `/analytics/spp_plus` return cached last-good within 100ms on DB/provider timeout.
  - TTLs align with plan (indicator 1h, spp 30m).
Estimate: M
Owner: (unset)
Tags: [core] [api] [cache] [tests]

- [ ] TASK: Price Backfill Worker/CLI (id: T-0019)
Why: Keep snapshots fresh without manual seeding.
Deliverables: worker task or CLI that fetches provider quotes for configured type_ids/region and inserts `orderbook_snapshots`.
Acceptance:
  - Idempotent upserts using unique `(region_id, type_id, side, ts)`.
  - Respects provider rate limits and polite cadence.
Estimate: M
Owner: (unset)
Tags: [ops] [db] [adapter]

- [ ] TASK: Frontend Calculator Uses Live Prices (id: T-0020)
Why: Replace placeholder prices with API-fed quotes to reflect real costs.
Deliverables: frontend/src/pages/Calculator.tsx updates to request `/prices/quotes` and update price map.
Acceptance:
  - On load, calculator fetches quotes for preloaded materials and updates totals.
  - Fallback to static prices when API fails.
Estimate: S
Owner: (unset)
Tags: [ui] [api]

# Sprint 2 — Frontend UX Overhaul

- [ ] TASK: Design System + Theme (id: T-0025)
Why: Establish sleek, modern look with purple/blue/green palette and reusable UI tokens.
Deliverables: frontend/src/styles.css with CSS variables (colors, spacing, typography), utility classes, README snippet.
Acceptance:
  - CSS variables define primary/secondary/accent shades and gradients.
  - Global layout uses new tokens; dark theme default.
Estimate: S
Owner: (unset)
Tags: [ui]

- [ ] TASK: Animated Background (EVE Map Web) (id: T-0026)
Why: Add shifting node/filament background reminiscent of EVE map.
Deliverables: frontend/src/components/BackgroundWeb.tsx (Canvas animation), integration in App layout.
Acceptance:
  - Background animates nodes and connecting filaments with gradient strokes (purple/blue/green).
  - Does not exceed 3% CPU on idle in dev; pauses on tab blur.
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Calculator UX Expansion (id: T-0027)
Why: Provide more options similar to reference image: structure presets, rig toggles, skill presets, blueprint selector.
Deliverables: updates to frontend/src/pages/Calculator.tsx with cards, toggles, and presets.
Acceptance:
  - User can choose blueprint (Nitrogen Fuel Blocks default, plus sample advanced hull/component), change rigs, and apply skill presets (All V, Industry IV, Custom).
  - Changes visibly update material quantities and job time.
Estimate: M
Owner: (unset)
Tags: [ui]

- [ ] TASK: Responsive Layout + Polish (id: T-0028)
Why: Ensure clean layout on laptop/desktop; mobile-friendly grid.
Deliverables: CSS grid/breakpoints, card components with glassmorphism style.
Acceptance:
  - Layout stacks on narrow widths; maintains readability and contrast.
Estimate: S
Owner: (unset)
Tags: [ui]

- [ ] TASK: UI Smoke Tests (id: T-0029)
Why: Basic confidence for critical interactions.
Deliverables: minimal vitest/RTL tests (or Playwright optional) for Calculator.
Acceptance:
  - Tests verify that changing skills and structure toggles updates displayed totals.
Estimate: S
Owner: (unset)
Tags: [ui] [tests]

- [ ] TASK: SDE Import Integration & Auto DB Upsert (id: T-0030)
Why: Ensure DB is populated with required SDE subsets whenever the importer runs.
Deliverables: utils/manage_sde.py defaults to upserting into Postgres; docs updated; optional `--no-db` flag.
Acceptance:
  - Running `python utils/manage_sde.py update --from-file <yaml>` updates JSON artifacts and upserts `type_ids`, `blueprints`, `structures`.
  - Manifest prevents redundant work; idempotent upserts verified via repeated runs.
Estimate: S
Owner: (unset)
Tags: [db] [ops]

- [ ] TASK: Frontend in Docker Compose (id: T-0031)
Why: One-command dev stack including UI without installing Node locally.
Deliverables: docker-compose.yml frontend service using Node image to run Vite dev server.
Acceptance:
  - `docker compose up` exposes frontend at 5173 and API at 8000; proxy routes work.
Estimate: S
Owner: (unset)
Tags: [ops] [ui]

- [ ] TASK: Celery Worker + Beat with Schedules (id: T-0032)
Why: Run recurring price refresh/backfill and indicator rebuild per plan cadences.
Deliverables: tasks.py Celery tasks; docker-compose worker + beat services; schedule config.
Acceptance:
  - `price_refresh` reads env `PRICE_TYPE_IDS` + `REGION_ID` + provider and inserts snapshots idempotently.
  - Beat triggers refresh every ~12m; logs confirm execution.
Estimate: M
Owner: (unset)
Tags: [ops] [adapter] [db]

- [ ] TASK: Analytics Cache Tests (id: T-0033)
Why: Prove cache-hit and last-good fallback behavior.
Deliverables: tests/services/test_analytics_cache.py using fakeredis and monkeypatching DB calls.
Acceptance:
  - First call computes and caches; second call returns cached when DB is unavailable.
Estimate: S
Owner: (unset)
Tags: [tests] [cache]

- [ ] TASK: Rig/Skill Rules (EVE Canonical) (id: T-0021)
Why: Apply correct per-group rig bonuses and skill multipliers for manufacturing/reactions.
Deliverables: frontend/lib/evecalc.ts with group-aware bonuses; docs link to assumptions.
Acceptance:
  - Adjusting activity/group updates ME/TE according to EVE rules.
  - Unit tests for calculation helper functions (UI-level).
Estimate: M
Owner: (unset)
Tags: [ui] [math] [tests]

- [ ] TASK: Metrics for RateLimiter (id: T-0022)
Why: Observe allowed/denied/delayed counts.
Deliverables: simple metrics exporter (e.g., `/metrics` or logs) incrementing counters by key.
Acceptance:
  - Counters exposed or logged; smoke test validates increments via a fake limiter.
Estimate: S
Owner: (unset)
Tags: [ops]

- [ ] TASK: Dev Docker Compose (API + Postgres + Redis) (id: T-0023)
Why: One-command local stack to avoid manual DB setup and ensure consistent env.
Deliverables: docker-compose.yml with API, Postgres (15), Redis (7), .env overrides.
Acceptance:
  - `docker compose up` starts services; API `/health/ready` reports ready after migrations.
  - Volumes persisted for Postgres and Redis.
Estimate: M
Owner: (unset)
Tags: [ops]

- [ ] TASK: CORS/Proxy Developer Experience (id: T-0024)
Why: Ensure frontend can talk to API without CORS issues.
Deliverables: CORS middleware defaults in FastAPI, Vite proxy config checked in.
Acceptance:
  - Frontend dev server (Vite) calls `/analytics` and `/prices` without CORS errors.
  - Document toggle to disable CORS when running via proxy.
Estimate: S
Owner: (unset)
Tags: [ui] [api]
