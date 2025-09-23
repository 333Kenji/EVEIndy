from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from indy_math.planner import (
    Character,
    Facility,
    Job,
    PlanningError,
    plan_window,
    recommend_assignments,
)


START = datetime(2024, 4, 1, 0, 0, 0)


def test_recommend_assignments_picks_fastest_character_and_facility() -> None:
    jobs = [
        Job(job_id="nf", activity="Manufacturing", runs=10, per_run_minutes=Decimal("12"), batch_size=5),
    ]
    characters = [
        Character(character_id=1, name="Slow", activity_slots={"Manufacturing": 10}, time_multipliers={"Manufacturing": Decimal("1.1")}),
        Character(character_id=2, name="Fast", activity_slots={"Manufacturing": 10}, time_multipliers={"Manufacturing": Decimal("0.9")}),
    ]
    facilities = [
        Facility(structure_id="rait", name="Raitaru", activity="Manufacturing", time_multiplier=Decimal("0.95")),
    ]

    assignments, unassigned = recommend_assignments(jobs, characters, facilities)
    assert not unassigned
    assert len(assignments) == 1
    assignment = assignments[0]
    assert assignment.character.character_id == 2
    assert assignment.facility and assignment.facility.structure_id == "rait"
    # Effective minutes per run = 12 * 0.9 * 0.95
    assert assignment.effective_minutes_per_run == Decimal("10.26")


def test_plan_window_staggers_batches_across_slots() -> None:
    jobs = [
        Job(job_id="advcomp", activity="Manufacturing", runs=12, per_run_minutes=Decimal("15"), batch_size=6),
    ]
    characters = [
        Character(
            character_id=7,
            name="Builder",
            activity_slots={"Manufacturing": 2},
            time_multipliers={"Manufacturing": Decimal("0.8")},
        )
    ]
    facilities = [Facility(structure_id="azbel", name="Azbel", activity="Manufacturing", time_multiplier=Decimal("0.9"))]

    end = START + timedelta(hours=8)
    result = plan_window(START, end, jobs, characters, facilities)

    plan = result.characters[7].activities["Manufacturing"]
    assert plan.slots == 2
    # Two batches of 6 runs each -> 6 runs * 15 minutes * 0.8 * 0.9 = 64.8 minutes per batch
    assert len(plan.tasks) == 2
    assert plan.tasks[0].slot_index == 0
    assert plan.tasks[1].slot_index == 1
    assert plan.tasks[0].end <= START + timedelta(minutes=65)
    assert plan.tasks[1].start == START


def test_plan_window_tracks_overflow_when_cutoff_hit() -> None:
    jobs = [Job(job_id="long", activity="Manufacturing", runs=20, per_run_minutes=Decimal("60"), batch_size=10)]
    characters = [Character(character_id=11, name="Solo", activity_slots={"Manufacturing": 1}, time_multipliers={"Manufacturing": Decimal("1.0")})]
    facilities: list[Facility] = []
    end = START + timedelta(hours=5)

    result = plan_window(START, end, jobs, characters, facilities)
    # First batch of 10 runs (600 minutes) already exceeds window -> overflow list populated
    assert not result.characters[11].activities["Manufacturing"].tasks
    assert result.overflow
    overflow_job = result.overflow[0]
    assert overflow_job.job_id == "long"
    assert overflow_job.runs == 10


def test_plan_window_validates_end_before_start() -> None:
    jobs = [Job(job_id="x", activity="Manufacturing", runs=1, per_run_minutes=Decimal("10"))]
    characters = [Character(character_id=1, name="A", activity_slots={"Manufacturing": 1})]
    with pytest.raises(PlanningError):
        plan_window(START, START, jobs, characters, [])

