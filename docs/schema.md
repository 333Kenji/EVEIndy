# Database Schema Overview

This document describes the initial EVEINDY database schema installed by `migrations/versions/20240416_01_initial_schema.py`.

## Extensions & Functions
- Enables `pgcrypto` to support UUID defaults via `gen_random_uuid()`.
- Defines `set_updated_at()` trigger function to keep `updated_at` columns synchronized on mutations.

## Core Tables
- **inventory** `(owner_scope, type_id)`
  - Tracks owner-scope (corp + alts) quantity and rolling-average cost per item.
  - Columns: `qty_on_hand NUMERIC(20,2)`, `avg_cost NUMERIC(28,4)`, `created_at`, `updated_at`.
  - Index: `ix_inventory_owner_scope_avg_cost` for valuation reporting.
- **inventory_by_loc** `(owner_scope, type_id, location_id)`
  - Breaks holdings into buckets (On-hand production, At Jita, Open Buy Orders / in-transit).
  - Columns include `qty_reserved` and `qty_in_transit` to support reservations and pipeline tracking.
  - Partial index `ix_inventory_by_loc_reserved` filters rows with reserved quantity.
- **industry_jobs** `(job_id)`
  - Captures character jobs with activity enum, run counts, timing, fees, and facility metadata.
  - Indexes on `(status, end_time)` for scheduling and `(owner_scope, status)` for corp views.
- **buy_orders** `(order_id)`
  - Owner-scope buy order intent with price, remaining quantity, and lifecycle status (`open|filled|cancelled`).
  - Indexes on `(owner_scope, status)` and `(type_id, region_id)` for availability decisions.
- **acquisitions** `(id UUID)`
  - Immutable ledger of inventory acquisitions from market fills or excess manufacturing outputs.
  - References `industry_jobs` (`ref_job_id`) and `buy_orders` (`ref_order_id`).
  - Enum `acquisition_source` enforces provenance (market, industry_excess, contract).
- **consumptions** `(id UUID)`
  - Logs consumption of inventory for jobs or write-offs with `consumption_reason` enum.
  - Indexed by `(ref_job_id, type_id)` for cost trace reconstruction.
- **consumption_log** `(id UUID)`
  - Audit trail for reservation releases and adjustments with optional notes.
  - Indexed by timestamp descending for operational review.
- **orderbook_snapshots** `(id UUID)`
  - Stores bid/ask depth metrics, spreads, and volatility summaries per region/type/side.
  - Unique constraint on `(region_id, type_id, side, ts)` prevents duplicate snapshots.
- **inventory_coverage_view**
  - Aggregates `inventory_by_loc` to produce totals for on-hand, reserved, and in-transit quantities.

## Data Integrity Highlights
- All monetary values use `NUMERIC(28,4)` and quantities use `NUMERIC(20,2)` per costing guardrails.
- Trigger `set_updated_at()` keeps `updated_at` in sync for inventory, location, job, and buy order tables.
- Enums (`job_activity`, `job_status`, `buy_order_status`, `acquisition_source`, `consumption_reason`, `order_side`) enforce allowed status transitions and provenance.
- Foreign keys use `ON UPDATE CASCADE` so changes to job/order identifiers from ESI sync propagate automatically.

## Migration Notes
- Run with `alembic upgrade head` using `DATABASE_URL` from the environment or `alembic.ini`.
- Downgrade tears down the view, tables, and enums in dependency-safe order.

