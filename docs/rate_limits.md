# Provider Rate Limits

- Central token-bucket RateLimiter with per-provider configuration (capacity, refill tokens/sec).
- Adapters call `block_until_allowed(key)` before outbound requests; retry/backoff (exponential + jitter) and circuit breakers remain in place.
- Metrics per key: `allowed`, `denied`, `delayed`. Expose later via metrics endpoint.
- Defaults:
  - ESI: capacity=10, refill=2 tokens/s.
  - Adam4EVE: capacity=1, refill=0.1 tokens/s (~10s per call).
  - Fuzzwork: capacity=1, refill=0.2 tokens/s (~5s per call).
- Configurable via environment variables surfaced in `Settings`.
