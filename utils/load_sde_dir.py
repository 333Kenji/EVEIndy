"""One-shot SDE loader.

Given a local SDE directory, find the important YAMLs and run the importer
in the correct order (types first, then blueprints). By default, this will
also upsert into Postgres using DATABASE_URL (see utils/manage_sde.py).

Usage:
  IndyCalculator/bin/python utils/load_sde_dir.py /path/to/extracted_sde \
    [--version vYYYY.MM.DD] [--no-db]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from utils import manage_sde


POSSIBLE_TYPES = (
    "typeIDs.yaml",
    "typeids.yaml",
)
POSSIBLE_BLUEPRINTS = (
    "industryBlueprints.yaml",
    "industryblueprints.yaml",
    "blueprints.yaml",
)


def _find_one(root: Path, candidates: Iterable[str]) -> Optional[Path]:
    root = root.resolve()
    for name in candidates:
        for p in root.rglob(name):
            if p.is_file():
                return p
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Load SDE from a directory")
    ap.add_argument("path", help="Path to extracted SDE directory")
    ap.add_argument("--version", default=None, help="Version label, e.g., vYYYY.MM.DD")
    ap.add_argument("--no-db", action="store_true", help="Skip DB upserts; only write JSON artifacts")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"Directory not found: {root}")

    types = _find_one(root, POSSIBLE_TYPES)
    bps = _find_one(root, POSSIBLE_BLUEPRINTS)

    if not types and not bps:
        raise SystemExit("Could not find typeIDs.yaml or industryBlueprints.yaml in the provided directory")

    # Import types first if present
    if types:
        manage_sde.update(
            argparse.Namespace(
                command="update",
                from_file=str(types),
                version=args.version,
                no_db=args.no_db,
            )
        )

    if bps:
        manage_sde.update(
            argparse.Namespace(
                command="update",
                from_file=str(bps),
                version=args.version,
                no_db=args.no_db,
            )
        )

    print("SDE directory load complete")


if __name__ == "__main__":
    main()

