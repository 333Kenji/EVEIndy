from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping

from indy_math.planner import (
    Assignment,
    Character,
    Facility,
    Job,
    PlanResult,
    PlanningError,
    plan_window,
    recommend_assignments,
)


def _parse_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        value = default
    try:
        return Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise PlanningError(f"Invalid decimal value: {value}") from exc


def _parse_characters(items: Iterable[Mapping[str, Any]]) -> List[Character]:
    characters: List[Character] = []
    for item in items:
        try:
            character_id = int(item["character_id"])
        except Exception as exc:  # noqa: BLE001
            raise PlanningError("character_id is required") from exc
        name = str(item.get("name") or f"Character {character_id}")
        activity_slots_raw = item.get("activity_slots") or {}
        if not isinstance(activity_slots_raw, Mapping):
            raise PlanningError("activity_slots must be a mapping")
        activity_slots = {str(k): int(v) for k, v in activity_slots_raw.items()}
        if not activity_slots:
            # Default to one manufacturing slot when omitted
            activity_slots = {"Manufacturing": int(item.get("slots", 1))}
        time_multipliers_raw = item.get("time_multipliers") or {}
        if not isinstance(time_multipliers_raw, Mapping):
            raise PlanningError("time_multipliers must be a mapping")
        time_multipliers = {str(k): _parse_decimal(v) for k, v in time_multipliers_raw.items()}
        characters.append(
            Character(
                character_id=character_id,
                name=name,
                activity_slots=activity_slots,
                time_multipliers=time_multipliers,
            )
        )
    return characters


def _parse_facilities(items: Iterable[Mapping[str, Any]]) -> List[Facility]:
    facilities: List[Facility] = []
    for item in items:
        try:
            structure_id = str(item["structure_id"])
            name = str(item.get("name") or structure_id)
            activity = str(item.get("activity") or "Manufacturing")
        except Exception as exc:  # noqa: BLE001
            raise PlanningError("structure entries must include structure_id") from exc
        time_multiplier = _parse_decimal(item.get("time_multiplier", "1.0"), default="1.0")
        system_id = item.get("system_id")
        facilities.append(
            Facility(
                structure_id=structure_id,
                name=name,
                activity=activity,
                time_multiplier=time_multiplier,
                system_id=int(system_id) if system_id is not None else None,
            )
        )
    return facilities


def _parse_jobs(items: Iterable[Mapping[str, Any]]) -> List[Job]:
    jobs: List[Job] = []
    for item in items:
        job_id_raw = item.get("job_id") or item.get("type_id")
        if job_id_raw is None:
            raise PlanningError("job entries require job_id or type_id")
        job_id = str(job_id_raw)
        activity = str(item.get("activity") or "Manufacturing")
        runs = int(item.get("runs", 0))
        if runs <= 0:
            raise PlanningError(f"Job {job_id} must have runs > 0")
        per_run_minutes = _parse_decimal(item.get("per_run_minutes", "0"))
        if per_run_minutes <= 0:
            raise PlanningError(f"Job {job_id} requires positive per_run_minutes")
        batch_size = int(item.get("batch_size", 1))
        priority = int(item.get("priority", 0))
        type_id = item.get("type_id")
        jobs.append(
            Job(
                job_id=job_id,
                activity=activity,
                runs=runs,
                per_run_minutes=per_run_minutes,
                batch_size=batch_size,
                priority=priority,
                type_id=int(type_id) if type_id is not None else None,
            )
        )
    return jobs


def _serialize_assignment(assignment: Assignment) -> Dict[str, Any]:
    facility = assignment.facility
    return {
        "job_id": assignment.job.job_id,
        "type_id": assignment.job.type_id,
        "character_id": assignment.character.character_id,
        "character_name": assignment.character.name,
        "activity": assignment.job.activity,
        "structure_id": facility.structure_id if facility else None,
        "structure_name": facility.name if facility else None,
        "effective_minutes_per_run": str(assignment.effective_minutes_per_run),
        "effective_multiplier": str(assignment.effective_multiplier),
    }


def _serialize_plan(result: PlanResult) -> Dict[str, Any]:
    characters = []
    total_runs = 0
    total_minutes = Decimal("0")
    for char_id, schedule in result.characters.items():
        activities: Dict[str, Any] = {}
        for activity, act_schedule in schedule.activities.items():
            tasks = []
            for task in act_schedule.tasks:
                total_runs += int(task.runs)
                total_minutes += task.duration_minutes
                tasks.append(
                    {
                        "job_id": task.job_id,
                        "type_id": task.type_id,
                        "runs": task.runs,
                        "slot_index": task.slot_index,
                        "activity": task.activity,
                        "start": task.start.isoformat(),
                        "end": task.end.isoformat(),
                        "duration_minutes": str(task.duration_minutes),
                        "structure_id": task.structure_id,
                        "structure_name": task.structure_name,
                    }
                )
            activities[activity] = {
                "slots": act_schedule.slots,
                "total_minutes": str(act_schedule.total_minutes),
                "tasks": tasks,
            }
        characters.append(
            {
                "character_id": char_id,
                "name": schedule.character.name,
                "activities": activities,
            }
        )

    overflow = [
        {
            "job_id": task.job_id,
            "runs": task.runs,
            "activity": task.activity,
            "structure_id": task.structure_id,
            "structure_name": task.structure_name,
            "start": task.start.isoformat(),
            "end": task.end.isoformat(),
        }
        for task in result.overflow
    ]

    unassigned = [
        {
            "job_id": job.job_id,
            "activity": job.activity,
            "runs": job.runs,
            "per_run_minutes": str(job.per_run_minutes),
        }
        for job in result.unassigned
    ]

    summary = {
        "total_runs": total_runs,
        "total_minutes": str(total_minutes.quantize(Decimal("0.0001"))),
    }

    return {
        "start": result.start.isoformat(),
        "end": result.end.isoformat(),
        "characters": characters,
        "assignments": [_serialize_assignment(a) for a in result.assignments],
        "overflow": overflow,
        "unassigned": unassigned,
        "summary": summary,
    }


def schedule_window(payload: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        start = datetime.fromisoformat(str(payload["start"]))
        duration_hours = int(payload.get("duration_hours", 168))
    except Exception as exc:  # noqa: BLE001
        raise PlanningError("Invalid start or duration_hours") from exc
    if duration_hours <= 0:
        raise PlanningError("duration_hours must be positive")

    characters = _parse_characters(payload.get("characters", []))
    facilities = _parse_facilities(payload.get("structures", []))
    jobs = _parse_jobs(payload.get("jobs", []))
    end = start + timedelta(hours=duration_hours)

    result = plan_window(start, end, jobs, characters, facilities)
    plan = _serialize_plan(result)
    plan["assumptions"] = {
        "start": plan["start"],
        "end": plan["end"],
        "duration_hours": duration_hours,
    }
    return plan


def recommend(payload: Mapping[str, Any]) -> Dict[str, Any]:
    characters = _parse_characters(payload.get("characters", []))
    facilities = _parse_facilities(payload.get("structures", []))
    jobs = _parse_jobs(payload.get("jobs", []))
    assignments, unassigned = recommend_assignments(jobs, characters, facilities)
    return {
        "assignments": [_serialize_assignment(a) for a in assignments],
        "unassigned": [
            {
                "job_id": job.job_id,
                "activity": job.activity,
                "runs": job.runs,
                "per_run_minutes": str(job.per_run_minutes),
            }
            for job in unassigned
        ],
    }

