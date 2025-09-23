"""Repository interfaces for database operations (testable via fakes).

Concrete implementations should live under app/repos/pg_* and use SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol, Sequence


JobActivity = Literal["manufacturing", "reaction", "invention", "research"]


@dataclass(frozen=True)
class Job:
    job_id: int
    owner_scope: str
    char_id: int
    type_id: int
    activity: JobActivity
    runs: int
    start_time: datetime
    end_time: datetime | None
    status: str
    location_id: int | None
    facility_id: int | None
    fees_isk: Decimal | None


class InventoryRepo(Protocol):
    def reserve_for_job(self, job: Job) -> None: ...
    def release_for_job(self, job: Job) -> None: ...
    def settle_job_outputs(self, job: Job) -> None: ...


class JobsRepo(Protocol):
    def upsert_jobs(self, owner_scope: str, jobs: Sequence[Job]) -> None: ...

