# Static Data Export (SDE) Workflow

- Local-only utility `python utils/manage_sde.py update --from-file path/to/sde.yaml [--version vYYYY.MM.DD]` downloads/parses and writes compact artifacts to `data/sde/`.
- By default, the importer also upserts parsed data into Postgres (`type_ids`, `blueprints`, `structures`); disable with `--no-db`.
- The CLI computes a checksum and updates a manifest so repeated runs with the same file are no-ops.
- Migrations add `type_ids`, `blueprints`, `structures`, `cost_indices` for convenient joins with live data.
- Production images must not bundle raw SDE; developers refresh SDE locally when CCP publishes updates.
