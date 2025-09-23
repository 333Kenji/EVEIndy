# SDE Auto-Downloader + Loader

Run a single command to fetch the latest CCP SDE and load the subsets we need into Postgres.

Usage
- Venv: `IndyCalculator/bin/python utils/fetch_and_load_sde.py`
- Options:
  - `--version vYYYY.MM.DD` override manifest label
  - `--dir /tmp/sde` download directory (default: `data/sde/_downloads`)
  - `--no-db` skip DB upserts (write JSON only)
  - `--force` re-download even if files already exist
  - `--base-url` alternate index page for mirrors (defaults to CCP static data page)

Behavior
- Discovers typeIDs.yaml(.bz2) and industryBlueprints.yaml(.bz2) links from the CCP static data page, downloads both, decompresses, then runs the importer in order (types → blueprints).
- Honors HTTP(S)_PROXY env vars; retries with exponential backoff.
- Upserts into Postgres by default; manage via `--no-db`.

Notes
- If CCP changes the static data page markup, set `--base-url` to a mirror and re-run.
- Attribution and integrity checks: see `docs/ATTRIBUTION.md`.
