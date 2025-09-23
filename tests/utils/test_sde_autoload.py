from __future__ import annotations

from pathlib import Path

from app import sde_autoload as sa


def write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_find_local_sde_files_yaml(tmp_path: Path) -> None:
    write(tmp_path / "typeIDs.yaml", "34: { name: { en: 'Tritanium' } }\n")
    write(tmp_path / "industryBlueprints.yaml", "{}\n")
    files = sa.find_local_sde_files(tmp_path)
    assert files is not None
    assert files.type_file.name.lower().endswith("typeids.yaml")
    assert files.bp_file.name.lower().endswith("industryblueprints.yaml")


def test_autoload_triggers_on_new_snapshot(tmp_path: Path, monkeypatch) -> None:
    write(tmp_path / "typeIDs.yaml", "34: { name: { en: 'Tritanium' } }\n")
    write(tmp_path / "industryBlueprints.yaml", "{}\n")
    # Ensure manifest checksum differs by deleting existing manifest
    mpath = Path("data/sde/manifest.json")
    if mpath.exists():
        mpath.unlink()
    called = {"n": 0}

    def fake_load_local(args):  # noqa: ANN001
        called["n"] += 1

    import utils.manage_sde as mod
    monkeypatch.setattr(mod, "load_local", fake_load_local)
    sa.load_if_new(tmp_path)
    assert called["n"] == 1

