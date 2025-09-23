from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence


ZERO = Decimal("0")


@dataclass(frozen=True)
class Facility:
    """Production facility metadata used for scheduling."""

    structure_id: str
    name: str
    activity: str
    time_multiplier: Decimal = Decimal("1.0")
    system_id: int | None = None


@dataclass(frozen=True)
class Character:
    """Builder configuration with available slots and time modifiers."""

    character_id: int
    name: str
    activity_slots: Mapping[str, int] = field(default_factory=dict)
    time_multipliers: Mapping[str, Decimal] = field(default_factory=dict)

    def slots_for(self, activity: str) -> int:
        return int(self.activity_slots.get(activity, 0))

    def multiplier_for(self, activity: str) -> Decimal:
        raw = self.time_multipliers.get(activity)
        if raw is None:
            return Decimal("1.0")
        return Decimal(str(raw))


@dataclass(frozen=True)
class Job:
    """Represents a production job request."""

    job_id: str
    activity: str
    runs: int
    per_run_minutes: Decimal
    batch_size: int = 1
    priority: int = 0
    type_id: int | None = None

    def batches(self) -> Iterable[int]:
        remaining = int(self.runs)
        size = max(1, int(self.batch_size))
        while remaining > 0:
            chunk = min(size, remaining)
            yield chunk
            remaining -= chunk


@dataclass(frozen=True)
class Assignment:
    """Recommended character/facility pairing for a job."""

    job: Job
    character: Character
    facility: Facility | None
    effective_minutes_per_run: Decimal
    effective_multiplier: Decimal


@dataclass
class ScheduledBatch:
    job_id: str
    runs: int
    start: datetime
    end: datetime
    slot_index: int
    activity: str
    duration_minutes: Decimal
    type_id: int | None = None
    structure_id: str | None = None
    structure_name: str | None = None


@dataclass
class ActivitySchedule:
    slots: int
    tasks: list[ScheduledBatch] = field(default_factory=list)

    @property
    def total_minutes(self) -> Decimal:
        total = ZERO
        for task in self.tasks:
            total += task.duration_minutes
        return total


@dataclass
class CharacterSchedule:
    character: Character
    activities: Dict[str, ActivitySchedule]


@dataclass
class PlanResult:
    start: datetime
    end: datetime
    assignments: Sequence[Assignment]
    characters: Dict[int, CharacterSchedule]
    overflow: list[ScheduledBatch]
    unassigned: list[Job]


class PlanningError(ValueError):
    """Raised when the planner cannot complete a schedule."""


def _as_decimal(value: int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def recommend_assignments(
    jobs: Sequence[Job],
    characters: Sequence[Character],
    facilities: Sequence[Facility],
) -> tuple[list[Assignment], list[Job]]:
    """Score characters + facilities for each job and pick the fastest combination.

    Returns a tuple of `(assignments, unassigned_jobs)`.
    """

    facility_by_activity: MutableMapping[str, list[Facility]] = {}
    for facility in facilities:
        facility_by_activity.setdefault(facility.activity.lower(), []).append(facility)
    for bucket in facility_by_activity.values():
        bucket.sort(key=lambda f: (f.time_multiplier, f.name))

    assignments: list[Assignment] = []
    unassigned: list[Job] = []
    sorted_jobs = sorted(jobs, key=lambda j: (j.priority, j.job_id))

    for job in sorted_jobs:
        activity_key = job.activity.lower()
        best: Assignment | None = None
        for character in sorted(characters, key=lambda c: c.character_id):
            slots = character.slots_for(job.activity)
            if slots <= 0:
                continue
            char_multiplier = character.multiplier_for(job.activity)
            facility_candidates = facility_by_activity.get(activity_key, [])
            if not facility_candidates:
                facility_candidates = [None]
            for facility in facility_candidates:
                facility_multiplier = facility.time_multiplier if facility else Decimal("1.0")
                effective_multiplier = _as_decimal(job.per_run_minutes) * char_multiplier * facility_multiplier
                if effective_multiplier <= ZERO:
                    raise PlanningError("Effective run duration must be positive")
                effective_minutes_per_run = effective_multiplier
                candidate = Assignment(
                    job=job,
                    character=character,
                    facility=facility,
                    effective_minutes_per_run=effective_minutes_per_run,
                    effective_multiplier=char_multiplier * facility_multiplier,
                )
                if best is None or candidate.effective_minutes_per_run < best.effective_minutes_per_run:
                    best = candidate
        if best is None:
            unassigned.append(job)
        else:
            assignments.append(best)
    return assignments, unassigned


def plan_window(
    start: datetime,
    end: datetime,
    jobs: Sequence[Job],
    characters: Sequence[Character],
    facilities: Sequence[Facility],
) -> PlanResult:
    """Generate a per-character schedule within the requested window."""

    if end <= start:
        raise PlanningError("End must be after start")
    assignments, unassigned = recommend_assignments(jobs, characters, facilities)

    schedules: Dict[int, CharacterSchedule] = {}
    availability: Dict[int, Dict[str, list[datetime]]] = {}

    for character in characters:
        activities: Dict[str, ActivitySchedule] = {}
        availability[character.character_id] = {}
        for activity, slot_count in character.activity_slots.items():
            slots = max(0, int(slot_count))
            activities[activity] = ActivitySchedule(slots=slots)
            availability[character.character_id][activity] = [start for _ in range(slots)]
        schedules[character.character_id] = CharacterSchedule(character=character, activities=activities)

    overflow: list[ScheduledBatch] = []

    for assignment in assignments:
        character = assignment.character
        activity = assignment.job.activity
        char_schedule = schedules[character.character_id]
        activity_schedule = char_schedule.activities.get(activity)
        if activity_schedule is None or activity_schedule.slots <= 0:
            overflow.append(
                ScheduledBatch(
                    job_id=assignment.job.job_id,
                    runs=assignment.job.runs,
                    start=end,
                    end=end,
                    slot_index=-1,
                    activity=activity,
                    duration_minutes=Decimal("0"),
                    type_id=assignment.job.type_id,
                    structure_id=assignment.facility.structure_id if assignment.facility else None,
                    structure_name=assignment.facility.name if assignment.facility else None,
                )
            )
            continue

        slot_times = availability[character.character_id][activity]
        for runs in assignment.job.batches():
            if not slot_times:
                overflow.append(
                    ScheduledBatch(
                        job_id=assignment.job.job_id,
                        runs=runs,
                        start=end,
                        end=end,
                        slot_index=-1,
                        activity=activity,
                        duration_minutes=Decimal("0"),
                        type_id=assignment.job.type_id,
                        structure_id=assignment.facility.structure_id if assignment.facility else None,
                        structure_name=assignment.facility.name if assignment.facility else None,
                    )
                )
                continue
            slot_index = min(range(len(slot_times)), key=lambda idx: (slot_times[idx], idx))
            slot_start = slot_times[slot_index]
            if slot_start < start:
                slot_start = start
            duration_minutes = assignment.effective_minutes_per_run * Decimal(runs)
            duration_minutes = duration_minutes.quantize(Decimal("0.0001"))
            if duration_minutes <= ZERO:
                raise PlanningError("Computed duration must be positive")
            slot_end = slot_start + timedelta(minutes=float(duration_minutes))
            batch = ScheduledBatch(
                job_id=assignment.job.job_id,
                runs=runs,
                start=slot_start,
                end=slot_end,
                slot_index=slot_index,
                activity=activity,
                duration_minutes=duration_minutes,
                type_id=assignment.job.type_id,
                structure_id=assignment.facility.structure_id if assignment.facility else None,
                structure_name=assignment.facility.name if assignment.facility else None,
            )
            if slot_end > end:
                overflow.append(batch)
            else:
                activity_schedule.tasks.append(batch)
                slot_times[slot_index] = slot_end

    for plan in schedules.values():
        for schedule in plan.activities.values():
            schedule.tasks.sort(key=lambda t: (t.start, t.slot_index, t.job_id))

    return PlanResult(
        start=start,
        end=end,
        assignments=assignments,
        characters=schedules,
        overflow=overflow,
        unassigned=unassigned,
    )

