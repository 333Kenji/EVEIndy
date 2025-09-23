"""SDE Manager utility.

CLI: `python utils/manage_sde.py update`

Responsibilities (scaffold):
- Download latest SDE YAML archive (offline in tests via fixtures).
- Detect new versions via checksum/manifest.
- Parse subsets needed for T2 production; write compact JSON or insert into Postgres.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import yaml  # type: ignore


DATA_ROOT = Path("data/sde")
MANIFEST = DATA_ROOT / "manifest.json"


@dataclass(frozen=True)
class SDEVersion:
    version: str
    checksum: str


def ensure_dirs() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)


def compute_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> Mapping[str, str] | None:
    if not MANIFEST.exists():
        return None
    return json.loads(MANIFEST.read_text())


def save_manifest(version: SDEVersion) -> None:
    MANIFEST.write_text(json.dumps({"version": version.version, "checksum": version.checksum}))


def _ccp_style_blueprints(doc: Mapping) -> bool:
    # CCP SDE style is usually mapping[typeID] -> { activities: { manufacturing: { materials:[], products:[] }, reaction: {...} } }
    return isinstance(doc, dict) and any(isinstance(v, dict) and "activities" in v for v in doc.values())


def parse_blueprints(yaml_doc: Mapping) -> Iterable[Mapping]:
    """Parse a minimal blueprint subset from a simplified YAML document.

    Expected structure:
      blueprints:
        - type_id: 123
          product_id: 456
          activity: manufacturing
          materials:
            - type_id: 34
              qty: 10
    """
    # 1) CCP SDE-style
    if _ccp_style_blueprints(yaml_doc):
        for type_id_str, entry in yaml_doc.items():
            try:
                type_id = int(type_id_str)
            except Exception:
                continue
            acts = entry.get("activities", {}) or {}
            for act_name in ("manufacturing", "reaction"):
                act = acts.get(act_name)
                if not act:
                    continue
                # Prefer explicit products list; otherwise skip
                products = act.get("products", []) or []
                materials = act.get("materials", []) or []
                for prod in products:
                    product_id = int(prod.get("typeID") or prod.get("type_id") or 0)
                    if not product_id:
                        continue
                    out_qty = int(prod.get("quantity") or prod.get("qty") or 1)
                    mats = [
                        {"type_id": int(m.get("typeID") or m.get("type_id")), "qty": int(m.get("quantity") or m.get("qty") or 0)}
                        for m in materials
                        if (m.get("typeID") or m.get("type_id"))
                    ]
                    yield {
                        "type_id": type_id,
                        "product_id": product_id,
                        "activity": "reaction" if act_name == "reaction" else "manufacturing",
                        "materials": mats,
                        "output_qty": out_qty,
                    }
        return

    # 2) Simplified custom format
    for bp in yaml_doc.get("blueprints", []) or []:
        yield {
            "type_id": int(bp["type_id"]),
            "product_id": int(bp["product_id"]),
            "activity": str(bp.get("activity", "manufacturing")),
            "materials": bp.get("materials", []),
        }


def parse_types(yaml_doc: Mapping) -> Iterable[Mapping]:
    # CCP SDE: typeIDs.yaml is mapping[typeID] -> { name: { en: "..." }, groupID: ..., categoryID?: via invGroups }
    if isinstance(yaml_doc, dict) and any(k for k in yaml_doc.keys() if isinstance(k, (int, str))):
        # Heuristic: top-level mapping with nested dicts containing 'name' or 'groupID'
        count = 0
        for key, val in yaml_doc.items():
            if isinstance(val, dict) and ("name" in val or "groupID" in val or "groupId" in val):
                name = val.get("name")
                if isinstance(name, dict):
                    # name: {en: "..."}
                    name = name.get("en") or next(iter(name.values()), "")
                yield {
                    "type_id": int(key),
                    "name": str(name or ""),
                    "group_id": int(val.get("groupID") or val.get("groupId") or 0),
                    "category_id": int(val.get("categoryID") or val.get("categoryId") or 0),
                    "meta": {k: v for k, v in val.items() if k not in {"name", "groupID", "groupId", "categoryID", "categoryId"}},
                }
                count += 1
        if count:
            return
    # Simplified format
    for t in yaml_doc.get("types", []) or []:
        yield {
            "type_id": int(t["type_id"]),
            "name": str(t.get("name", "")),
            "group_id": int(t.get("group_id", 0)),
            "category_id": int(t.get("category_id", 0)),
            "meta": t.get("meta", {}),
        }


def parse_structures(yaml_doc: Mapping) -> Iterable[Mapping]:
    for s in yaml_doc.get("structures", []) or []:
        yield {
            "structure_id": int(s["structure_id"]),
            "type": str(s.get("type", "")),
            "rig_slots": int(s.get("rig_slots", 0)),
            "bonuses": s.get("bonuses", {}),
        }


def detect_rigs_from_types(yaml_doc: Mapping) -> Iterable[Mapping]:
    """Detect structure rigs from type names.

    Heuristic mapping based on CCP naming like "Standup M-Set Manufacturing Material Efficiency I".
    """
    if not isinstance(yaml_doc, dict):
        return []
    for key, val in yaml_doc.items():
        try:
            name = val.get("name")
            if isinstance(name, dict):
                name = name.get("en") or next(iter(name.values()), "")
            if not name:
                continue
            low = str(name).lower()
            if "standup" not in low and "rig" not in low and "set" not in low:
                continue
            activity = None
            me_bonus = 0.0
            te_bonus = 0.0
            if "manufactur" in low:
                activity = "Manufacturing"
            elif "reaction" in low:
                activity = "Reactions"
            elif "refin" in low or "reprocess" in low:
                activity = "Refining"
            elif "science" in low or "research" in low:
                activity = "Science"
            if "material efficiency" in low or "me" in low:
                me_bonus = 0.02
            if "time efficiency" in low or "te" in low:
                te_bonus = 0.02
            if activity:
                yield {
                    "rig_id": int(key),
                    "name": name,
                    "activity": activity,
                    "me_bonus": me_bonus,
                    "te_bonus": te_bonus,
                }
        except Exception:
            continue

def upsert_sde_to_db(payload: Mapping, dsn: str) -> None:
    import sqlalchemy as sa
    from sqlalchemy import text

    engine = sa.create_engine(dsn)
    with engine.begin() as conn:
        for t in parse_types(payload):
            conn.execute(text(
                """
                INSERT INTO type_ids(type_id, name, group_id, category_id, meta)
                VALUES (:type_id, :name, :group_id, :category_id, :meta)
                ON CONFLICT (type_id) DO UPDATE SET
                    name=EXCLUDED.name,
                    group_id=EXCLUDED.group_id,
                    category_id=EXCLUDED.category_id,
                    meta=EXCLUDED.meta
                """
            ), t)
        for bp in parse_blueprints(payload):
            conn.execute(text(
                """
                INSERT INTO blueprints(type_id, product_id, activity, materials, output_qty)
                VALUES (:type_id, :product_id, :activity, :materials, :output_qty)
                ON CONFLICT (type_id, product_id, activity) DO UPDATE SET
                    materials=EXCLUDED.materials,
                    output_qty=EXCLUDED.output_qty
                """
            ), bp)
        # Derive and upsert materials set
        material_ids = set()
        for bp in parse_blueprints(payload):
            for m in bp.get("materials", []) or []:
                mid = m.get("type_id") or m.get("typeID")
                if mid:
                    material_ids.add(int(mid))
        for mid in material_ids:
            conn.execute(text(
                """
                INSERT INTO industry_materials(type_id, source)
                VALUES (:mid, 'bp_material')
                ON CONFLICT (type_id) DO UPDATE SET updated_at=timezone('utc', now())
                """
            ), {"mid": mid})
        for s in parse_structures(payload):
            conn.execute(text(
                """
                INSERT INTO structures(structure_id, type, rig_slots, bonuses)
                VALUES (:structure_id, :type, :rig_slots, :bonuses)
                ON CONFLICT (structure_id) DO UPDATE SET
                    type=EXCLUDED.type,
                    rig_slots=EXCLUDED.rig_slots,
                    bonuses=EXCLUDED.bonuses
                """
            ), s)


def update(args: argparse.Namespace) -> None:
    """Update SDE data from a local file path (offline-friendly).

    Use `--from-file` to provide a YAML source for tests/development.
    """

    ensure_dirs()
    manifest = load_manifest()
    src = Path(args.from_file) if args.from_file else None
    if src and src.exists():
        checksum = compute_checksum(src)
        version = SDEVersion(version=args.version or "dev", checksum=checksum)
        prev = manifest.get("checksum") if manifest else None
        if prev == checksum:
            print("SDE up-to-date; no changes")
            return
        # Parse minimal subsets (stubs for now)
        payload = yaml.safe_load(src.read_text())
        # Write compact JSON placeholders
        (DATA_ROOT / "blueprints.json").write_text(json.dumps(list(parse_blueprints(payload))))
        (DATA_ROOT / "type_ids.json").write_text(json.dumps(list(parse_types(payload))))
        (DATA_ROOT / "structures.json").write_text(json.dumps(list(parse_structures(payload))))
        # Upsert parsed SDE to DB by default (can disable with --no-db)
        if not getattr(args, "no_db", False):
            from app.config import Settings
            dsn = Settings().database_url
            upsert_sde_to_db(payload, dsn)
        save_manifest(version)
        print("SDE updated")
        return

    raise SystemExit("--from-file is required in this offline scaffold")


def load_local(args: argparse.Namespace) -> None:
    root = Path(args.dir)
    if not root.exists():
        raise SystemExit(f"SDE directory not found: {root}")
    # Prefer YAML; fallback to JSON
    def find_one(names: list[str]) -> Path | None:
        for n in names:
            p = root / n
            if p.exists():
                return p
        return None

    type_file = find_one(["typeIDs.yaml", "typeids.yaml"]) or find_one(["typeIDs.json", "typeids.json"])
    bp_file = find_one(["industryBlueprints.yaml", "industryblueprints.yaml", "blueprints.yaml"]) or find_one([
        "industryBlueprints.json",
        "industryblueprints.json",
        "blueprints.json",
    ])
    if not (type_file and bp_file):
        raise SystemExit("Missing required SDE files (typeIDs and industryBlueprints) in data/SDE/_downloads")

    contents_types = (
        yaml.safe_load(type_file.read_text()) if type_file.suffix.lower() == ".yaml" else json.loads(type_file.read_text())
    )
    contents_bp = (
        yaml.safe_load(bp_file.read_text()) if bp_file.suffix.lower() == ".yaml" else json.loads(bp_file.read_text())
    )
    ensure_dirs()
    (DATA_ROOT / "type_ids.json").write_text(json.dumps(list(parse_types(contents_types))))
    # Filter blueprints to likely T2 frigates/cruisers using DB name hints if present
    bps = list(parse_blueprints(contents_bp))
    try:
        import sqlalchemy as sa
        from sqlalchemy import text as _text
        from app.config import Settings as _Settings

        engine = sa.create_engine(_Settings().database_url)
        prod_ids = {int(x["product_id"]) for x in bps if x.get("product_id")}
        name_map: dict[int, str] = {}
        if prod_ids:
            with engine.connect() as conn:
                rows = conn.execute(_text("select type_id,name from type_ids where type_id = any(:ids)"), {"ids": list(prod_ids)}).fetchall()
                name_map = {int(r[0]): r[1] for r in rows}
        filtered = []
        for bp in bps:
            pid = int(bp["product_id"]) if bp.get("product_id") else None
            name = (name_map.get(pid, "") or "").lower()
            if any(t in name for t in ("frigate", "cruiser")) and (" ii" in name or "tech ii" in name or " t2" in name):
                filtered.append(bp)
        if filtered:
            bps = filtered
    except Exception:
        pass
    (DATA_ROOT / "blueprints.json").write_text(json.dumps(bps))

    if not args.no_db:
        from app.config import Settings
        dsn = Settings().database_url
        upsert_sde_to_db(contents_types, dsn)
        import sqlalchemy as sa
        from sqlalchemy import text as _text
        engine = sa.create_engine(dsn)
        with engine.begin() as conn:
            # Upsert rigs detected from types
            for rig in detect_rigs_from_types(contents_types):
                conn.execute(_text(
                    """
                    INSERT INTO rigs(rig_id, name, activity, me_bonus, te_bonus)
                    VALUES (:rig_id, :name, :activity, :me_bonus, :te_bonus)
                    ON CONFLICT (rig_id) DO UPDATE SET
                        name=EXCLUDED.name,
                        activity=EXCLUDED.activity,
                        me_bonus=EXCLUDED.me_bonus,
                        te_bonus=EXCLUDED.te_bonus
                    """
                ), rig)
            for bp in bps:
                conn.execute(
                    _text(
                        """
                        INSERT INTO blueprints(type_id, product_id, activity, materials, output_qty)
                        VALUES (:type_id, :product_id, :activity, :materials, :output_qty)
                        ON CONFLICT (type_id, product_id, activity) DO UPDATE SET
                            materials=EXCLUDED.materials,
                            output_qty=EXCLUDED.output_qty
                        """
                    ),
                    bp,
                )
            # Upsert industry_materials derived from filtered blueprints
            mats = set()
            for bp in bps:
                for m in bp.get("materials", []) or []:
                    mid = m.get("type_id") or m.get("typeID")
                    if mid:
                        mats.add(int(mid))
            for mid in mats:
                conn.execute(_text(
                    """
                    INSERT INTO industry_materials(type_id, source) VALUES (:mid, 'bp_material')
                    ON CONFLICT (type_id) DO UPDATE SET updated_at=timezone('utc', now())
                    """
                ), {"mid": mid})

            # Universe IDs (optional): mapRegions, mapConstellations, mapSolarSystems YAMLs
            for fname, kind, parent in (
                ("mapRegions.yaml", "region", None),
                ("mapConstellations.yaml", "constellation", "regionID"),
                ("mapSolarSystems.yaml", "system", "constellationID"),
            ):
                p = (Path(args.dir) / fname)
                if not p.exists():
                    continue
                data = yaml.safe_load(p.read_text())
                for key, row in (data.items() if isinstance(data, dict) else []):
                    _id = int(key)
                    name = row.get("name", {}).get("en") if isinstance(row.get("name"), dict) else row.get("name")
                    parent_id = int(row.get(parent)) if (parent and row.get(parent)) else None
                    conn.execute(_text(
                        """
                        INSERT INTO universe_ids(id, name, kind, parent_id)
                        VALUES (:id, :name, :kind, :parent)
                        ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, kind=EXCLUDED.kind, parent_id=EXCLUDED.parent_id
                        """
                    ), {"id": _id, "name": name, "kind": kind, "parent": parent_id})
    print("SDE load-local completed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage SDE data for EVEINDY")
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("update", help="Fetch, parse, and store SDE subsets; also upserts to DB by default")
    up.add_argument("--from-file", help="Path to local YAML file for offline parse")
    up.add_argument("--version", help="Version string for manifest", default=None)
    up.add_argument("--no-db", action="store_true", help="Skip DB upserts; only write JSON artifacts")
    ld = sub.add_parser("load-local", help="Load SDE from data/SDE/_downloads and upsert subset")
    ld.add_argument("--dir", default="data/SDE/_downloads")
    ld.add_argument("--no-db", action="store_true")
    ld.add_argument("--version", default=None)

    args = parser.parse_args()

    if args.command == "update":
        update(args)
    elif args.command == "load-local":
        load_local(args)


if __name__ == "__main__":
    main()
