# Redis Key Strategy

| Pattern | TTL | Last-Good TTL | Description |
| --- | --- | --- | --- |
| `price:{provider}:{region_id}:{type_id}` | 900s | 86,400s | Top-of-book price quotes per provider. |
| `index:{system_id}:{activity}` | 86,400s | 86,400s | System cost indices cached per activity. |
| `indicator:{region_id}:{type_id}` | 3,600s | 86,400s | Moving averages / Bollinger / depth summaries. |
| `spp:{type_id}:{region_id}:{params_hash}` | 1,800s | 86,400s | SPP⁺ recommendations keyed by scenario hash. |

Values are stored as envelopes containing `stored_at`, `ttl`, and `value`. When the primary key expires, the `:last_good` shadow key surfaces the most recent payload and marks it as stale for API responses.
