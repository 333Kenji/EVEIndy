from decimal import Decimal

import pytest

from indy_math.costing import (
    CostContext,
    CostingError,
    InventoryEntry,
    MaterialRequirement,
    Recipe,
    cost_item,
)


@pytest.fixture
def base_context() -> CostContext:
    inventory = {
        100: InventoryEntry(type_id=100, available_qty=Decimal("10"), avg_cost=Decimal("5")),
    }
    acquisition_costs = {100: Decimal("6"), 200: Decimal("18")}
    recipes = {
        200: Recipe(
            type_id=200,
            output_qty=Decimal("1"),
            batch_size=1,
            materials=(MaterialRequirement(type_id=100, quantity=Decimal("2")),),
            job_fee=Decimal("2.5"),
        ),
    }
    return CostContext(inventory=inventory, recipes=recipes, acquisition_costs=acquisition_costs)


def test_cost_item_consumes_inventory_first(base_context: CostContext) -> None:
    result = cost_item(100, Decimal("4"), base_context)
    assert result.consumed_cost == Decimal("20.0000")
    assert result.consumed_qty == Decimal("4")
    assert result.excess_to_inventory == {}
    assert result.trace.entries[0].source == "inventory"


def test_cost_item_manufacture_with_excess(base_context: CostContext) -> None:
    result = cost_item(200, Decimal("2"), base_context)
    assert result.consumed_qty == Decimal("2")
    assert result.excess_to_inventory == {}
    assert result.consumed_cost == Decimal("25.0000")
    assert "manufacture" in {entry.source for entry in result.trace.entries}
    assert result.fee_split["consumed_fee"] == Decimal("5.0000")


def test_cost_item_propagates_excess(base_context: CostContext) -> None:
    updated_recipe = Recipe(
        type_id=200,
        output_qty=Decimal("2"),
        batch_size=2,
        materials=(MaterialRequirement(type_id=100, quantity=Decimal("3")),),
        job_fee=Decimal("4"),
    )
    ctx = CostContext(
        inventory=base_context.inventory,
        recipes={200: updated_recipe},
        acquisition_costs=base_context.acquisition_costs,
    )
    result = cost_item(200, Decimal("1"), ctx)
    assert result.excess_to_inventory[200].quantity == Decimal("1")
    assert result.excess_to_inventory[200].unit_cost == Decimal("9.5000")
    assert result.fee_split["consumed_fee"] == Decimal("2.0000")
    assert result.fee_split["excess_fee"] == Decimal("2.0000")


def test_cost_item_deterministic(base_context: CostContext) -> None:
    first = cost_item(200, Decimal("1"), base_context)
    second = cost_item(200, Decimal("1"), base_context)
    assert first == second


def test_cost_item_missing_recipe_raises(base_context: CostContext) -> None:
    with pytest.raises(CostingError):
        cost_item(999, Decimal("1"), base_context)
