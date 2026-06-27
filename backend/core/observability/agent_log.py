"""
CrimePatrol — Agent Execution Logger
Writes structured agent run records to the agent_execution_log table
and emits structured log lines for real-time observability.
"""
import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from backend.core.observability.logger import get_logger

logger = get_logger(__name__)


class AgentExecutionLogger:
    """
    Context manager that logs agent start/end/error to both
    the structured log stream and the agent_execution_log DB table.

    Usage::

        async with AgentExecutionLogger(session, run_id, "WeatherAgent", area_id):
            result = await weather_agent.run(state)
    """

    def __init__(
        self,
        db_session: Any,
        run_id: UUID,
        agent_name: str,
        area_id: UUID | None = None,
        input_summary: dict[str, Any] | None = None,
    ) -> None:
        self.db_session = db_session
        self.run_id = run_id
        self.agent_name = agent_name
        self.area_id = area_id
        self.input_summary = input_summary
        self._start_time: float = 0.0

    async def __aenter__(self) -> "AgentExecutionLogger":
        from backend.infrastructure.database.models.agent_execution_log import (
            AgentExecutionLogModel,
        )
        from datetime import datetime, timezone

        self._start_time = time.perf_counter()
        self._log_entry = AgentExecutionLogModel(
            run_id=self.run_id,
            agent_name=self.agent_name,
            status="started",
            started_at=datetime.now(timezone.utc),
            area_id=self.area_id,
            input_summary=self.input_summary,
        )
        self.db_session.add(self._log_entry)
        await self.db_session.flush()

        logger.info(
            "agent_started",
            agent=self.agent_name,
            run_id=str(self.run_id),
        )
        return self

    async def complete(self, output_summary: dict[str, Any] | None = None) -> None:
        from datetime import datetime, timezone

        duration_ms = round((time.perf_counter() - self._start_time) * 1000)
        self._log_entry.status = "completed"
        self._log_entry.completed_at = datetime.now(timezone.utc)
        self._log_entry.duration_ms = duration_ms
        self._log_entry.output_summary = output_summary
        await self.db_session.flush()

        logger.info(
            "agent_completed",
            agent=self.agent_name,
            run_id=str(self.run_id),
            duration_ms=duration_ms,
        )

    async def fail(self, error: Exception) -> None:
        from datetime import datetime, timezone

        duration_ms = round((time.perf_counter() - self._start_time) * 1000)
        self._log_entry.status = "failed"
        self._log_entry.completed_at = datetime.now(timezone.utc)
        self._log_entry.duration_ms = duration_ms
        self._log_entry.error_message = str(error)
        await self.db_session.flush()

        logger.error(
            "agent_failed",
            agent=self.agent_name,
            run_id=str(self.run_id),
            duration_ms=duration_ms,
            error=str(error),
        )

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            await self.fail(exc_val)
            return False   # re-raise the exception
        return False
