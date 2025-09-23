from __future__ import annotations

from pathlib import Path

import httpx

import utils.fetch_and_load_sde as fl


class FakeClient:
    def __init__(self, html: str, files: dict[str, bytes]) -> None:
        self._html = html
        self._files = files

    def get(self, url: str, headers: dict | None = None):  # noqa: ANN001
        class R:
            def __init__(self, text=None, content=None):
                self.text = text
                self._content = content
                self.status_code = 200

            def raise_for_status(self):
                pass

            def iter_bytes(self):  # for streaming mock compatibility
                yield self._content

        if url.endswith("static-data"):
            return R(text=self._html)
        # file download
        # Return a simple object with stream-like interface
        return R(content=self._files[Path(url).name])

    def stream(self, method: str, url: str, headers: dict | None = None):  # noqa: ANN001
        return self.get(url, headers=headers)


def test_fetch_and_load_discovers_downloads_and_loads(tmp_path, monkeypatch):
    html = '<a href="https://example.com/typeIDs.yaml.bz2?v=2025.01.01">typeIDs</a>\n' \
           '<a href="https://example.com/industryBlueprints.yaml.bz2?v=2025.01.01">bps</a>'
    files = {
        'typeIDs.yaml.bz2': fl.bz2.compress(b"34:\n  name:\n    en: Tritanium\n  groupID: 18\n"),
        'industryBlueprints.yaml.bz2': fl.bz2.compress(b"{}\n"),
    }
    fake = FakeClient(html, files)
    monkeypatch.setattr(fl, "_http_client", lambda: fake)
    # Do not call manage_sde.update; just assert functions progress. Patch manage_sde.update
    calls = {"n": 0}
    import utils.manage_sde as mod
    monkeypatch.setattr(mod, "update", lambda ns: calls.__setitem__("n", calls["n"] + 1))

    version = fl.fetch_and_load(out_dir=tmp_path, no_db=True, base_url="https://developers.eveonline.com/static-data")
    assert version in ("dev", "2025.01.01")
    assert calls["n"] == 2
    assert (tmp_path / "typeIDs.yaml").exists() or (tmp_path / "typeIDs.yaml.bz2").exists()


def test_fetch_and_load_checksum_mismatch_raises(tmp_path, monkeypatch):
    html = '<a href="https://example.com/typeIDs.yaml">typeIDs</a>\n' \
           '<a href="https://example.com/industryBlueprints.yaml">bps</a>'
    files = {
        'typeIDs.yaml': b"content-A",
        'industryBlueprints.yaml': b"{}\n",
    }
    fake = FakeClient(html, files)
    monkeypatch.setattr(fl, "_http_client", lambda: fake)
    import pytest
    with pytest.raises(SystemExit):
        fl.fetch_and_load(out_dir=tmp_path, no_db=True, base_url="https://developers.eveonline.com/static-data", sha_types="deadbeef")

