from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import zipfile

from apscheduler.schedulers.background import BackgroundScheduler


SDE_DROP_DIR = Path("data/SDE/_downloads")
SUBSET_MANIFEST = Path("data/sde/manifest.json")


@dataclass
class SDEFiles:
    type_file: Path
    bp_file: Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_from_zip(zpath: Path, out_dir: Path) -> None:
    with zipfile.ZipFile(zpath, "r") as z:
        for name in z.namelist():
            lower = name.lower()
            if lower.endswith("typeids.yaml") or lower.endswith("industryblueprints.yaml") or lower.endswith("blueprints.yaml"):
                target = out_dir / Path(name).name
                if not target.exists():
                    z.extract(name, out_dir)
                    (out_dir / name).rename(target)


def find_local_sde_files(root: Path = SDE_DROP_DIR) -> Optional[SDEFiles]:
    if not root.exists():
        return None
    # If zip present, extract relevant YAMLs
    for z in root.glob("*.zip"):
        _extract_from_zip(z, root)
    # Prefer YAML
    type_file = None
    for n in ("typeIDs.yaml", "typeids.yaml"):
        p = root / n
        if p.exists():
            type_file = p
            break
    if not type_file:
        for n in ("typeIDs.json", "typeids.json"):
            p = root / n
            if p.exists():
                type_file = p
                break
    bp_file = None
    for n in ("industryBlueprints.yaml", "industryblueprints.yaml", "blueprints.yaml"):
        p = root / n
        if p.exists():
            bp_file = p
            break
    if not bp_file:
        for n in ("industryBlueprints.json", "industryblueprints.json", "blueprints.json"):
            p = root / n
            if p.exists():
                bp_file = p
                break
    if type_file and bp_file:
        return SDEFiles(type_file=type_file, bp_file=bp_file)
    return None


def compute_drop_checksum(files: SDEFiles) -> str:
    # Combined checksum over both files
    return hashlib.sha256((_sha256(files.type_file) + _sha256(files.bp_file)).encode()).hexdigest()


def manifest_checksum() -> Optional[str]:
    if not SUBSET_MANIFEST.exists():
        return None
    try:
        m = json.loads(SUBSET_MANIFEST.read_text())
        # Backward compatible with previous single-file manifest; fall back to checksum field
        if "type_ids" in m and "blueprints" in m:
            return hashlib.sha256((m["type_ids"]["sha256"] + m["blueprints"]["sha256"]).encode()).hexdigest()
        return m.get("checksum")
    except Exception:
        return None


def load_if_new(root: Path = SDE_DROP_DIR) -> Optional[str]:
    files = find_local_sde_files(root)
    if not files:
        return None
    new_sum = compute_drop_checksum(files)
    old_sum = manifest_checksum()
    if new_sum == old_sum:
        return None
    # Import via manage_sde.load_local
    from utils import manage_sde  # local import to avoid early import during app startup

    manage_sde.load_local(
        type("Args", (), {"dir": str(root), "no_db": False, "version": None})
    )
    return new_sum


def schedule_autoload() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # First immediate run
    try:
        load_if_new()
    except Exception:
        # Prevent hard failure on startup
        pass
    # Periodic scan every 6 hours
    scheduler.add_job(load_if_new, "interval", hours=6, id="sde_autoload_scan")
    scheduler.start()
    return scheduler

