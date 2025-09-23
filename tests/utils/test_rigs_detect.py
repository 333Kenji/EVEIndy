from __future__ import annotations

from utils.manage_sde import detect_rigs_from_types


def test_detect_rigs_from_types():
    doc = {
        "100000": {"name": {"en": "Standup M-Set Manufacturing Material Efficiency I"}},
        "100001": {"name": {"en": "Standup M-Set Manufacturing Time Efficiency I"}},
        "100010": {"name": {"en": "Something Else"}},
    }
    rigs = list(detect_rigs_from_types(doc))
    acts = {r["activity"] for r in rigs}
    assert "Manufacturing" in acts
    assert any(r["me_bonus"] > 0 for r in rigs)
    assert any(r["te_bonus"] > 0 for r in rigs)

