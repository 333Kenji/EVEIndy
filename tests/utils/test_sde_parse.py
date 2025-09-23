from __future__ import annotations

import yaml

from utils.manage_sde import parse_blueprints, parse_types


def test_parse_blueprints_ccp_style() -> None:
    doc = yaml.safe_load(
        """
        12345:
          activities:
            manufacturing:
              materials:
                - typeID: 34
                  quantity: 10
              products:
                - typeID: 67890
                  quantity: 1
            reaction:
              materials:
                - typeID: 35
                  quantity: 5
              products:
                - typeID: 54321
                  quantity: 1
        """
    )
    out = list(parse_blueprints(doc))
    assert any(o["activity"] == "manufacturing" and o["product_id"] == 67890 for o in out)
    assert any(o["activity"] == "reaction" and o["product_id"] == 54321 for o in out)


def test_parse_types_ccp_style() -> None:
    doc = yaml.safe_load(
        """
        34:
          name:
            en: Tritanium
          groupID: 18
        35:
          name:
            en: Pyerite
          groupID: 18
        """
    )
    out = list(parse_types(doc))
    assert any(o["type_id"] == 34 and o["name"] == "Tritanium" for o in out)
