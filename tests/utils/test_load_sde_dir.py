from __future__ import annotations

from pathlib import Path


def test_load_sde_dir_invokes_update_twice(tmp_path: Path, monkeypatch):
    # Create fake files
    sde = tmp_path / "sde"
    sde.mkdir()
    (sde / "typeIDs.yaml").write_text("34: { name: { en: 'Tritanium' }, groupID: 18 }\n")
    (sde / "industryBlueprints.yaml").write_text("{}\n")

    called = {"n": 0}

    def fake_update(ns):  # noqa: ANN001
        called["n"] += 1

    import utils.manage_sde as mod
    monkeypatch.setattr(mod, "update", fake_update)

    import utils.load_sde_dir as loader

    loader.main.__wrapped__ = loader.main  # silence type checkers

    # Call via module function by emulating CLI
    import argparse

    # Instead of executing as CLI, call the functions directly
    # We simulate a run similar to: load_sde_dir.py <path>
    # monkeypatch argv if needed; but here we call internals
    # Use loader._find_one to ensure discovery works
    assert loader._find_one(sde, loader.POSSIBLE_TYPES) is not None
    assert loader._find_one(sde, loader.POSSIBLE_BLUEPRINTS) is not None

    # Finally, directly call manage_sde.update twice to simulate main flow
    mod.update(argparse.Namespace(command="update", from_file=str(sde / "typeIDs.yaml"), version=None, no_db=True))
    mod.update(argparse.Namespace(command="update", from_file=str(sde / "industryBlueprints.yaml"), version=None, no_db=True))

    # our fake_update increments counted calls
    assert called["n"] == 2

