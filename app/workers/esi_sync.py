"""ESI sync worker logic (idempotent by design).

This module avoids direct DB calls; instead it accepts repository interfaces so
it can be unit tested without a real database.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Sequence

from app.providers.esi import ESIClient, IndustryJob
from app.repos import InventoryRepo, Job, JobsRepo


def _map_job(owner_scope: str, src: IndustryJob) -> Job:
    return Job(
        job_id=src.job_id,
        owner_scope=owner_scope,
        char_id=src.installer_id,
        type_id=src.blueprint_type_id,
        activity=src.status,  # Note: in real impl, map ESI activity separately
        runs=src.runs,
        start_time=src.start_date,
        end_time=src.end_date,
        status=src.status,
        location_id=src.location_id,
        facility_id=None,
        fees_isk=Decimal("0"),
    )


def sync_industry_jobs(owner_scope: str, esi: ESIClient, jobs_repo: JobsRepo, inv_repo: InventoryRepo) -> None:
    """Fetch and upsert jobs, then adjust reservations based on state.

    Idempotency:
    - Upserts replace existing rows with the same `job_id`.
    - Reservations are applied for `active` jobs and released for `delivered`/`cancelled`.
    - Completed jobs trigger settlement of outputs exactly once (enforced by DB-level idempotency in real impl).
    """

    jobs_resp = esi.list_industry_jobs(owner_scope)
    jobs = [_map_job(owner_scope, j) for j in jobs_resp.data]
    jobs_repo.upsert_jobs(owner_scope, jobs)

    for job in jobs:
        if job.status in {"active", "queued"}:
            inv_repo.reserve_for_job(job)
        elif job.status in {"delivered", "cancelled"}:
            inv_repo.release_for_job(job)
            if job.status == "delivered":
                inv_repo.settle_job_outputs(job)

