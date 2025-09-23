"""Consume-only costing functions with deterministic behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP, getcontext
from math import ceil
from typing import Dict, Iterable, Mapping, Sequence

ZERO = Decimal("0")
ONE = Decimal("1")

getcontext().prec = 28


@dataclass(frozen=True)
class InventoryEntry:
    type_id: int
    available_qty: Decimal
    avg_cost: Decimal


@dataclass(frozen=True)
class MaterialRequirement:
    type_id: int
    quantity: Decimal


@dataclass(frozen=True)
class Recipe:
    type_id: int
    output_qty: Decimal
    batch_size: int
    materials: Sequence[MaterialRequirement]
    job_fee: Decimal = ZERO


@dataclass(frozen=True)
class CostContext:
    inventory: Mapping[int, InventoryEntry]
    recipes: Mapping[int, Recipe]
    acquisition_costs: Mapping[int, Decimal]


@dataclass(frozen=True)
class CostTraceEntry:
    type_id: int
    quantity: Decimal
    source: str
    unit_cost: Decimal
    total_cost: Decimal
    details: Mapping[str, Decimal | int]


@dataclass(frozen=True)
class CostTrace:
    entries: Sequence[CostTraceEntry] = field(default_factory=tuple)

    def extend(self, other: Iterable[CostTraceEntry]) -> "CostTrace":
        return CostTrace(entries=(*self.entries, *tuple(other)))


@dataclass(frozen=True)
class ExcessRecord:
    quantity: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class CostResult:
    consumed_cost: Decimal
    consumed_qty: Decimal
    excess_to_inventory: Mapping[int, ExcessRecord]
    fee_split: Mapping[str, Decimal]
    trace: CostTrace


class CostingError(ValueError):
    """Raised when costing cannot be completed with the supplied context."""


def _decimal(value: int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _clamp_to_inventory(entry: InventoryEntry, requested: Decimal) -> Decimal:
    return min(requested, entry.available_qty)


def _merge_excess(
    base: Dict[int, ExcessRecord],
    addition: Mapping[int, ExcessRecord],
) -> None:
    for type_id, record in addition.items():
        if type_id in base:
            existing = base[type_id]
            total_qty = existing.quantity + record.quantity
            if total_qty == ZERO:
                base[type_id] = ExcessRecord(quantity=ZERO, unit_cost=record.unit_cost)
                continue
            weighted_cost = (
                (existing.unit_cost * existing.quantity) + (record.unit_cost * record.quantity)
            ) / total_qty
            base[type_id] = ExcessRecord(quantity=total_qty, unit_cost=weighted_cost)
        else:
            base[type_id] = record


def _merge_fees(base: Dict[str, Decimal], addition: Mapping[str, Decimal]) -> None:
    for key, value in addition.items():
        base[key] = base.get(key, ZERO) + value


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def cost_item(
    type_id: int,
    qty_needed: int | float | Decimal,
    ctx: CostContext,
    _stack: Sequence[int] | None = None,
) -> CostResult:
    """Calculate deterministic consume-only cost for the requested item quantity."""

    required = _decimal(qty_needed)
    if required <= ZERO:
        raise CostingError("qty_needed must be greater than zero")

    stack = tuple(_stack or ())
    if type_id in stack:
        raise CostingError(f"Detected recursive dependency cycle for type_id={type_id}")

    remaining = required
    consumed_cost = ZERO
    trace_entries: list[CostTraceEntry] = []
    excess: Dict[int, ExcessRecord] = {}
    fees: Dict[str, Decimal] = {}

    inventory_entry = ctx.inventory.get(type_id)
    if inventory_entry:
        available = _clamp_to_inventory(inventory_entry, remaining)
        if available > ZERO:
            unit_cost = _quantize(inventory_entry.avg_cost)
            line_cost = _quantize(unit_cost * available)
            consumed_cost += line_cost
            remaining -= available
            trace_entries.append(
                CostTraceEntry(
                    type_id=type_id,
                    quantity=available,
                    source="inventory",
                    unit_cost=unit_cost,
                    total_cost=line_cost,
                    details={"consumed": available},
                )
            )

    if remaining <= ZERO:
        return CostResult(
            consumed_cost=_quantize(consumed_cost),
            consumed_qty=required,
            excess_to_inventory=excess,
            fee_split=fees,
            trace=CostTrace(trace_entries),
        )

    recipe = ctx.recipes.get(type_id)
    if recipe:
        runs = max(1, ceil((remaining / recipe.output_qty)))
        produced_qty = Decimal(runs) * recipe.output_qty
        next_stack = (*stack, type_id)

        material_cost = ZERO
        for requirement in recipe.materials:
            child_qty = Decimal(runs) * requirement.quantity
            child_result = cost_item(requirement.type_id, child_qty, ctx, next_stack)
            material_cost += child_result.consumed_cost
            trace_entries.extend(child_result.trace.entries)
            _merge_excess(excess, child_result.excess_to_inventory)
            _merge_fees(fees, child_result.fee_split)

        job_fee_total = recipe.job_fee * Decimal(runs)

        total_cost = material_cost + job_fee_total
        if produced_qty <= ZERO:
            raise CostingError("Recipe output quantity must be positive")
        unit_cost = _quantize(total_cost / produced_qty)

        deliver_qty = min(produced_qty, remaining)
        consumed_cost += _quantize(unit_cost * deliver_qty)
        remaining -= deliver_qty

        excess_qty = produced_qty - deliver_qty
        if excess_qty > ZERO:
            excess_record = ExcessRecord(quantity=excess_qty, unit_cost=unit_cost)
            _merge_excess(excess, {type_id: excess_record})

        if job_fee_total > ZERO:
            consumed_fee = _quantize(job_fee_total * (deliver_qty / produced_qty))
            excess_fee = _quantize(job_fee_total - consumed_fee)
            if consumed_fee > ZERO:
                fees["consumed_fee"] = fees.get("consumed_fee", ZERO) + consumed_fee
            if excess_qty > ZERO and excess_fee > ZERO:
                fees["excess_fee"] = fees.get("excess_fee", ZERO) + excess_fee

        trace_entries.append(
            CostTraceEntry(
                type_id=type_id,
                quantity=produced_qty,
                source="manufacture",
                unit_cost=unit_cost,
                total_cost=_quantize(total_cost),
                details={
                    "runs": Decimal(runs),
                    "deliver_qty": deliver_qty,
                    "excess_qty": excess_qty,
                    "job_fee": job_fee_total,
                },
            )
        )

    elif type_id in ctx.acquisition_costs:
        unit_cost = _quantize(ctx.acquisition_costs[type_id])
        line_cost = _quantize(unit_cost * remaining)
        consumed_cost += line_cost
        trace_entries.append(
            CostTraceEntry(
                type_id=type_id,
                quantity=remaining,
                source="acquisition",
                unit_cost=unit_cost,
                total_cost=line_cost,
                details={"purchased": remaining},
            )
        )
        remaining = ZERO
    else:
        raise CostingError(f"No recipe or acquisition cost for type_id={type_id}")

    if remaining > ZERO:
        raise CostingError(
            f"Insufficient coverage for type_id={type_id}; remaining {remaining} after costing"
        )

    quantized_fees = {key: _quantize(value) for key, value in fees.items()}
    normalized_excess = {
        key: ExcessRecord(
            quantity=record.quantity,
            unit_cost=_quantize(record.unit_cost),
        )
        for key, record in excess.items()
    }

    return CostResult(
        consumed_cost=_quantize(consumed_cost),
        consumed_qty=required,
        excess_to_inventory=normalized_excess,
        fee_split=quantized_fees,
        trace=CostTrace(trace_entries),
    )
