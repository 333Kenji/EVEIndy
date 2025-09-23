"""Fetch and load the latest CCP SDE (YAML) in one command.

This tool:
- Discovers the latest SDE links from CCP's static data page
- Downloads industryBlueprints.yaml(.bz2) and typeIDs.yaml(.bz2)
- Decompresses archives
- Invokes manage_sde.update() in the correct order (types → blueprints)

Environment-aware:
- Honors HTTP(S)_PROXY env vars via httpx defaults
- Retries with exponential backoff and jitter

CLI:
  python utils/fetch_and_load_sde.py \
    [--version vYYYY.MM.DD] [--dir /tmp/sde] [--no-db] [--force]

Notes:
- This file writes to a working directory (default: ./data/sde/_downloads)
- By default, it upserts parsed data into Postgres (DATABASE_URL) via manage_sde
"""

from __future__ import annotations

import argparse
import bz2
import os
import re
import shutil
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Optional, Tuple

import httpx
from tenacity import Retrying, stop_after_attempt, wait_random_exponential

# Robust import to support both `python -m utils.fetch_and_load_sde` and
# direct execution `python utils/fetch_and_load_sde.py` from project root.
try:  # pragma: no cover - trivial import guard
    from utils import manage_sde  # type: ignore
except Exception:  # noqa: BLE001
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))
    from utils import manage_sde  # type: ignore


CCP_STATIC_DATA_URL = "https://developers.eveonline.com/static-data"

TYPE_RE = re.compile(r"typeids?\.ya?ml(\.bz2)?", re.IGNORECASE)
BP_RE = re.compile(r"industryblueprints\.ya?ml(\.bz2)?|blueprints\.ya?ml(\.bz2)?", re.IGNORECASE)
VER_RE = re.compile(r"v?([0-9]{4}\.[0-9]{2}\.[0-9]{2})")


@dataclass
class SDEAssets:
    typeids_url: str
    blueprints_url: str
    version: str


def _http_client() -> httpx.Client:
    # httpx honors HTTP(S)_PROXY from env by default; set a sensible timeout
    return httpx.Client(timeout=30.0, follow_redirects=True)


def discover_latest_assets(base_url: str = CCP_STATIC_DATA_URL, client: Optional[httpx.Client] = None) -> SDEAssets:
    c = client or _http_client()
    resp = c.get(base_url)
    resp.raise_for_status()
    html = resp.text
    # naive scraping of links
    links = re.findall(r"href=\"([^\"]+)\"", html)
    type_url = None
    bp_url = None
    version = None
    for href in links:
        if TYPE_RE.search(href) and not type_url:
            type_url = href if href.startswith("http") else httpx.URL(base_url).join(href).human_repr()
        if BP_RE.search(href) and not bp_url:
            bp_url = href if href.startswith("http") else httpx.URL(base_url).join(href).human_repr()
        m = VER_RE.search(href)
        if m and not version:
            version = m.group(1)
    if not (type_url and bp_url):
        raise RuntimeError("Could not discover SDE asset links on CCP static data page")
    if not version:
        version = "dev"
    return SDEAssets(typeids_url=type_url, blueprints_url=bp_url, version=version)


def _download_with_retry(url: str, dest: Path, client: Optional[httpx.Client] = None, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return dest
    c = client or _http_client()
    # Support simple resume via Range if partial exists
    tmp = dest.with_suffix(dest.suffix + ".part")
    headers = {}
    if tmp.exists():
        headers["Range"] = f"bytes={tmp.stat().st_size}-"

    def _do() -> None:
        with c.stream("GET", url, headers=headers) as r:
            r.raise_for_status()
            mode = "ab" if "Range" in headers else "wb"
            with tmp.open(mode) as f:
                for chunk in r.iter_bytes():
                    if chunk:
                        f.write(chunk)
        tmp.rename(dest)

    retry = Retrying(stop=stop_after_attempt(5), wait=wait_random_exponential(min=1, max=10), reraise=True)
    for attempt in retry:
        with attempt:
            _do()
    return dest


def _maybe_decompress(path: Path) -> Path:
    if path.suffix.lower() == ".bz2":
        out = path.with_suffix("")
        with bz2.open(path, "rb") as src, out.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        return out
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_manifest(dir_: Path, version: str, type_path: Path, bp_path: Path) -> None:
    (dir_).mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": version,
        "type_ids": {"file": type_path.name, "sha256": _sha256(type_path)},
        "blueprints": {"file": bp_path.name, "sha256": _sha256(bp_path)},
    }
    (dir_ / "manifest.json").write_text(json.dumps(manifest, indent=2))


def fetch_and_load(version: Optional[str] = None, out_dir: Optional[Path] = None, no_db: bool = False, force: bool = False, base_url: str = CCP_STATIC_DATA_URL, sha_types: Optional[str] = None, sha_blueprints: Optional[str] = None) -> str:
    out = out_dir or Path("data/sde/_downloads")
    out.mkdir(parents=True, exist_ok=True)
    client = _http_client()
    assets = discover_latest_assets(base_url=base_url, client=client)
    if version:
        assets = SDEAssets(typeids_url=assets.typeids_url, blueprints_url=assets.blueprints_url, version=version)
    # Download
    type_path = _download_with_retry(assets.typeids_url, out / Path(assets.typeids_url).name, client, force)
    bp_path = _download_with_retry(assets.blueprints_url, out / Path(assets.blueprints_url).name, client, force)
    # Decompress if needed
    type_yaml = _maybe_decompress(type_path)
    bp_yaml = _maybe_decompress(bp_path)
    # Optional checksum verification
    if sha_types:
        actual = _sha256(type_yaml)
        if actual.lower() != sha_types.lower() and not force:
            raise SystemExit(f"typeIDs checksum mismatch: expected {sha_types}, got {actual}. Use --force to override.")
    if sha_blueprints:
        actual = _sha256(bp_yaml)
        if actual.lower() != sha_blueprints.lower() and not force:
            raise SystemExit(f"blueprints checksum mismatch: expected {sha_blueprints}, got {actual}. Use --force to override.")

    # Import types first, then blueprints
    ns_common = {"command": "update", "version": assets.version, "no_db": no_db}
    manage_sde.update(argparse.Namespace(**ns_common, from_file=str(type_yaml)))
    manage_sde.update(argparse.Namespace(**ns_common, from_file=str(bp_yaml)))
    # Write manifest with computed hashes
    _write_manifest(out, assets.version, type_yaml, bp_yaml)
    return assets.version


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch and load latest CCP SDE")
    ap.add_argument("--version", default=None, help="Override version label (for manifest)")
    ap.add_argument("--dir", dest="out_dir", default=None, help="Download directory (default data/sde/_downloads)")
    ap.add_argument("--no-db", action="store_true", help="Do not upsert into Postgres; only write JSON")
    ap.add_argument("--force", action="store_true", help="Force re-download even if files exist")
    ap.add_argument("--base-url", default=CCP_STATIC_DATA_URL, help="Alternate base URL (for mirrors/testing)")
    ap.add_argument("--sha256-types", dest="sha_types", default=None, help="Expected SHA-256 for typeIDs.yaml (post-decompress)")
    ap.add_argument("--sha256-blueprints", dest="sha_blueprints", default=None, help="Expected SHA-256 for industryBlueprints.yaml (post-decompress)")
    args = ap.parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else None
    ver = fetch_and_load(version=args.version, out_dir=out_dir, no_db=args.no_db, force=args.force, base_url=args.base_url, sha_types=args.sha_types, sha_blueprints=args.sha_blueprints)
    print(f"SDE fetched and loaded (version={ver})")


if __name__ == "__main__":
    main()
