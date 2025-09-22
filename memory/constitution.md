This constitution governs EVEINDY, the EVE Online industry and market analysis agent, and defines non-negotiable rules that bind every future specification, implementation, deployment, and operational procedure.

## Purpose & Scope
EVEINDY orchestrates manufacturing, inventory control, and market intelligence for corporation-plus-alt operations, and this constitution binds all contributors and automated agents to these guardrails across design, code, data flows, infrastructure, and product decisions.

## Architecture Principles (Non-negotiable)
- Maintain all industry formulas as deterministic pure functions; reject contributions that introduce side effects, shared state, I/O, or nondeterministic dependencies inside math modules.
- Source inventory state exclusively from the Postgres owner-scope (corp+alts) rolling-average valuation tables; disallow additional per-lot or per-character valuation stores.
- Calculate job costs using only inputs consumed by the active job; route excess outputs to inventory valuation with their allocated input and fee shares instead of charging the job.
- Forbid automatic build-versus-buy decisions in calculators; specs must treat building as the default and rely on separate market-analysis signals to recommend buys.
- Make SPP+ forecasts lead-time aware by starting projections at listing time after production completes and factoring queue depth, historical price drift, and liquidity inputs.
- Track items only in the On-hand (production), At Jita (including in-transit for availability), and Open Buy Orders buckets; reject materials sell-order buckets or additional location tiers.

## Data Sources & Update Cadence
- Consume ESI endpoints for industry jobs, assets, skills, and system cost indices only within published cache timers and enforce throttles to stay below rate limits.
- Retrieve price and liquidity data via pluggable Adam4EVE or Fuzzwork providers, caching responses with timestamps and refreshing on a polite cadence (~10-15 min for prices, daily for indices).
- Wrap every external data provider with an interface that implements retries with exponential backoff and circuit-breaker protection before surfacing data to the app.

## Persistence & Caching Rules
- Store durable state (inventory, jobs, acquisitions, consumptions, buy orders, snapshots, telemetry) exclusively in Postgres schemas managed by migrations.
- Use Redis only for ephemeral caches of prices, indices, and indicator outputs; expire entries according to their data cadence.
- Update inventory rolling-average valuation only on acquisitions (market fills or manufactured excess); consuming inventory decreases quantity without modifying average cost.
- Create reservations for inputs when a job starts and release or settle them immediately on job completion within the same transaction.

## Planning, Costing & Fees
- Enforce integer batch sizes for every production tier (reactions, components, hulls) in planning and cost calculators.
- Compute job fees using executed run counts and pro-rate fees between consumed outputs and excess outputs.
- Record excess outputs into inventory at completion with a cost basis equal to their allocated inputs plus associated fee share.

## Market Analysis & SPP+
- Maintain daily metrics per hull and region for sell volume, bid-ask spread, price volatility, and shallow order book depth.
- Project SPP+ queue depth to listing time using demand depletion and estimated new listings while incorporating price drift when scoring sales probability.
- Generate batch-size recommendations that maximize expected fills over configurable horizons (default 3-day and 7-day settings).

## Tech Stack Constraints
- Implement backend services in Python FastAPI with worker workloads handled by Celery or APScheduler.
- Persist data in Postgres and cache ephemeral computations in Redis; do not introduce alternative primary stores.
- Ship the frontend as React with TanStack Query for data fetching and caching.
- Maintain a Python virtual environment named IndyCalculator, manage dependencies via pinned requirements.txt, and enforce ruff linting plus black formatting.
- Deliver cloud-ready containers that read secrets from environment variables and expose health, liveness, and readiness endpoints.

## Quality Gates
- Cover 100% of ISK-affecting formulas with unit tests and keep overall test coverage at or above 85%.
- Include determinism tests for every declared pure function to confirm identical outputs for identical inputs.
- Apply schema migrations for all database changes; reject ad-hoc DDL executed from application code or scripts outside the migration framework.
- Require each PR to include updated tests, a CHANGELOG.md snippet, and a performance note whenever it touches a documented hot path.

## Performance & Reliability
- Deliver price and index cache reads with a P95 latency under 150 ms; computational endpoints may respond asynchronously but must return the last known good cached result within 100 ms.
- Apply retry backoff with jitter on every external call and enforce rate-limit guards before dispatch.
- Design job completion handlers to be idempotent and wrap inventory mutations in transactions that guarantee exactly-once updates.

## Security & Privacy
- Manage secrets exclusively via environment variables or approved secret managers; never commit them to source control.
- Store ESI tokens encrypted at rest and request only the minimum scopes required for EVEINDY features.
- Record immutable audit logs for inventory changes and job state transitions with actor, timestamp, and context.

## UX Principles
- Display cost breakdowns that trace consumed inputs, allocated fee shares, and capitalized excess outputs for every job.
- Render inventory coverage bars for On-hand, At Jita, and Open Buy Orders buckets showing days of coverage.
- Provide interactive SPP+ what-if controls for lead time, price ticks, and batch size adjustments.

## Governance & Process
- Mark features Done only when tests pass, documentation is updated, schema migrations are applied, and performance budgets are verified.
- Route all work through feature branches merged via reviewed PRs that use squash merge.
- Version public APIs semantically and ship database migrations with every release that modifies schema.
- Change this constitution only through a dedicated PR that includes a completed Constitution Update Checklist at the top of this file.

## Out-of-Scope (for now)
- Do not pursue GPU or deep-learning forecasting capabilities.
- Avoid implementing lot-based valuation models.
- Exclude automatic long-haul logistics planning features.
