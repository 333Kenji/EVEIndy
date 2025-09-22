# Overview
EVEINDY is an agent that tracks EVE Online industry jobs, multi-character inventories, and market movements so it can surface profitable manufacturing batches, grounded in current assets and production queues.

# Problem Statement
- Current industry calculators treat manufacturing as stateless, forcing manual reconciliation between production runs and materials on hand.
- They ignore in-production reserves, so planners double-allocate inputs or lose track of what will complete next.
- Excess or byproduct materials are usually expensed immediately, skewing profitability because rolling-average costs are never capitalized.
- Build-versus-buy insights are detached from the inventory ledger and rolling averages, leaving managers without trustworthy signals tied to actual holdings.

# Users & Goals
- **Industrialist operating multiple toons** needs unified visibility of jobs, inputs, and outputs across characters and structures.
- **Corporation production manager** needs to align corp-level inventory, job queues, and market outlook when assigning work.
- Goals:
  - Track inventory and industry jobs in real time across corp and alts.
  - Compute manufacturing costs using rolling-average valuations tied to holdings.
  - Forecast market liquidity with SPP⁺ indicators that anticipate lead times and queue depth.
  - Recommend profitable ships and components to build next.
  - Balance build queues across characters to honor reservations and skill constraints.

# In-Scope Functional Requirements
- Maintain inventory buckets for On-hand (production), At Jita (including in-transit), and Open Buy Orders, all reconciled to rolling-average cost per material.
- Update rolling-average valuations per item at the owner scope whenever acquisitions occur and apply them to costing outputs.
- Represent industry jobs, schedules, and reservations so the system always knows which materials are committed and when runs finish.
- Produce job costing that charges only consumed inputs while capitalizing excess outputs back into inventory with their fair cost share.
- Calculate job fees on executed runs and pro-rate them across consumed items and excess outputs.
- Run market analysis over recent history, including moving averages, Bollinger bands, and shallow depth metrics per hull and region.
- Generate SPP⁺ sell-probability forecasts that incorporate production lead time, queue depth, demand depletion, and price drift before listing.
- Recommend batch sizes (e.g., build two hulls vs three) that maximize expected fills within a configurable time horizon such as 3 or 7 days.

# Out-of-Scope for v1
- Logistics planning or contract hauling workflows.
- Machine-learning forecasting beyond moving averages plus volatility tracking.
- Automatic build-versus-buy execution; only advisory signals are produced.

# Constraints & Dependencies
- Integrate with ESI endpoints for industry jobs, assets, character skills, and system cost indices while honoring cache timers and rate limits.
- Pull price and liquidity data from Adam4EVE or Fuzzwork via pluggable providers with cached responses.
- Deliver a React frontend backed by a FastAPI service layer to support the workflows above.

# Acceptance Criteria / Success Metrics
- Inventory across corp and alts reflects rolling-average cost and matches external ledger snapshots within tolerance.
- Active production queues display reservations, expected completion timestamps, and material commitments.
- Market analysis plus SPP⁺ outputs align with historical fill outcomes within an agreed deviation band.
- Batch recommendations optimize expected fills for 3- and 7-day horizons based on current inventory and forecasts.
- With identical input data, the system produces deterministic outputs for costing, reservations, and recommendations.
