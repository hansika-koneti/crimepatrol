"""
CrimePatrol — APScheduler Implementation
Wraps APScheduler behind the BaseScheduler abstract interface.
Swap this file for an airflow_impl.py to migrate orchestration
without touching any business logic.
"""
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.core.observability.logger import get_logger

logger = get_logger(__name__)


class APSchedulerBackend:
    """
    Concrete scheduler using APScheduler (AsyncIO mode).

    Scheduled jobs:
      - ETL pipeline:     hourly
      - Model monitoring: daily 06:00
      - Daily report:     daily 07:00
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    def schedule_job(
        self,
        fn: Callable,
        cron: str,
        job_id: str,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """
        Schedule a coroutine function with a cron expression.

        Args:
            fn:     Async callable to execute.
            cron:   Standard 5-field cron string (e.g. '0 * * * *').
            job_id: Unique identifier for this job.
            kwargs: Optional keyword arguments passed to fn at runtime.
        """
        fields = cron.split()
        trigger = CronTrigger(
            minute=fields[0],
            hour=fields[1],
            day=fields[2],
            month=fields[3],
            day_of_week=fields[4],
        )
        self._scheduler.add_job(
            fn,
            trigger=trigger,
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True,
            misfire_grace_time=300,   # allow up to 5min late start
        )
        logger.info("job_scheduled", job_id=job_id, cron=cron)

    def start(self) -> None:
        self._scheduler.start()
        logger.info("scheduler_started", backend="apscheduler")

    def shutdown(self, wait: bool = True) -> None:
        self._scheduler.shutdown(wait=wait)
        logger.info("scheduler_stopped", backend="apscheduler")

    def get_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]
