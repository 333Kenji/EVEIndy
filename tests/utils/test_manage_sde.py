from __future__ import annotations

import json
from pathlib import Path

from types import SimpleNamespace
from utils.manage_sde import (
    DATA_ROOT,
    MANIFEST,
    compute_checksum,
    ensure_dirs,
    load_manifest,
    save_manifest,
    update,
)


def test_manifest_roundtrip(tmp_path: Path) -> None:
    # Redirect data root
    orig = DATA_ROOT
    orig_manifest = MANIFEST
    try:
        # Monkeypatch by assigning module globals (simple approach)
        from utils import manage_sde as mod

        mod.DATA_ROOT = tmp_path / "data/sde"
        mod.MANIFEST = mod.DATA_ROOT / "manifest.json"

        mod.ensure_dirs()
        assert mod.MANIFEST.exists() is False
        mod.save_manifest(mod.SDEVersion(version="v0", checksum="abc"))
        loaded = mod.load_manifest()
        assert loaded["version"] == "v0"
        assert loaded["checksum"] == "abc"
    finally:
        # restore
        from utils import manage_sde as mod

        mod.DATA_ROOT = orig
        mod.MANIFEST = orig_manifest


def test_update_from_file_and_idempotent(tmp_path: Path) -> None:
    from utils import manage_sde as mod

    # Redirect data root
    orig_root = mod.DATA_ROOT
    orig_manifest = mod.MANIFEST
    try:
        mod.DATA_ROOT = tmp_path / "data/sde"
        mod.MANIFEST = mod.DATA_ROOT / "manifest.json"
        mod.ensure_dirs()

        # Create a simple YAML payload (structure irrelevant for scaffold)
        src = tmp_path / "sde.yaml"
        src.write_text("{}\n")

        args = SimpleNamespace(from_file=str(src), version="v1", command="update")
        update(args)

        # Files created
        assert (mod.DATA_ROOT / "blueprints.json").exists()
        assert (mod.DATA_ROOT / "type_ids.json").exists()
        assert (mod.DATA_ROOT / "structures.json").exists()

        # Second run with same file acts as no-op (manifest unchanged)
        before = load_manifest()
        update(args)
        after = load_manifest()
        assert before == after
    finally:
        mod.DATA_ROOT = orig_root
        mod.MANIFEST = orig_manifest
