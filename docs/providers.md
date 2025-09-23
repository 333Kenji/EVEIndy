# Provider Adapters

## Adam4EVE
- Endpoint: `GET {base_url}/market/type/{type_id}/region/{region_id}`.
- Retries: up to 5 attempts with exponential backoff (1–5s jitter).
- Circuit breaker: opens after 3 consecutive failures (configurable via constructor).
- Response schema: `{bid, ask, volatility, depth:{qty_1pct, qty_5pct}, updated}`.
- Returns `PriceQuote` with UTC timestamp and bid/ask/mid/depth fields.

## Fuzzwork
- Endpoint: `GET {base_url}/orders/type/{type_id}/region/{region_id}`.
- Same retry/backoff/circuit breaker behavior as Adam4EVE.
- Response schema: `{buy:{price, volume}, sell:{price, volume}, depth:{qty_1pct, qty_5pct}, generated, volatility}`.

## ESI
- Endpoints:
  - `GET {base_url}/industry/jobs/{owner_scope}` (with `include_completed=true`).
  - `GET {base_url}/assets/{owner_scope}`.
  - `GET {base_url}/industry/systems/{system_id}`.
  - `GET {base_url}/skills/{character_id}`.
- Authorization: `Bearer <token>` header supplied by injected token provider.
- Retries: up to 5 attempts with exponential backoff (1–6s jitter).
- Circuit breaker: opens after 5 consecutive failures by default.
- Responses validate against `IndustryJob`, `Asset`, `CostIndex`, and `CharacterSkills` models.
- The `Expires` header is parsed and returned with each `ESIResponse` to respect cache windows.
