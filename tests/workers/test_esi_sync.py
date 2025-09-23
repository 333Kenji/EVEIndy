from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Sequence

from app.providers.esi import ESIClient, IndustryJob
from app.repos import InventoryRepo, Job, JobsRepo
from app.workers.esi_sync import sync_industry_jobs


class FakeESI:
    def __init__(self, jobs: Sequence[IndustryJob]) -> None:
        self._jobs = jobs

    def list_industry_jobs(self, owner_scope: str):  # type: ignore[override]
        # Mimic ESIResponse
        from dataclasses import dataclass

        @dataclass
        class Resp:
            data: Sequence[IndustryJob]
            expires: None = None

        return Resp(self._jobs)


class FakeJobsRepo:
    def __init__(self) -> None:
        self.upserts: List[Job] = []

    def upsert_jobs(self, owner_scope: str, jobs: Sequence[Job]) -> None:
        self.upserts.extend(jobs)


class FakeInvRepo:
    def __init__(self) -> None:
        self.reserved: List[int] = []
        self.released: List[int] = []
        self.settled: List[int] = []

    def reserve_for_job(self, job: Job) -> None:
        self.reserved.append(job.job_id)

    def release_for_job(self, job: Job) -> None:
        self.released.append(job.job_id)

    def settle_job_outputs(self, job: Job) -> None:
        self.settled.append(job.job_id)


def test_sync_industry_jobs_idempotent_paths() -> None:
    jobs = [
        IndustryJob(
            job_id=1,
            blueprint_type_id=603,
            runs=2,
            status="active",
            start_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
            end_date=None,
            installer_id=123,
            location_id=60003760,
        ),
        IndustryJob(
            job_id=2,
            blueprint_type_id=603,
            runs=1,
            status="delivered",
            start_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 4, 1, 12, tzinfo=timezone.utc),
            installer_id=123,
            location_id=60003760,
        ),
    ]

    esi = FakeESI(jobs)
    jrepo = FakeJobsRepo()
    irepo = FakeInvRepo()

    sync_industry_jobs("corp", esi, jrepo, irepo)

    assert set(irepo.reserved) == {1}
    assert set(irepo.released) == {2}
    assert set(irepo.settled) == {2}
    # Upserts called with two jobs
    assert len(jrepo.upserts) == 2

