from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class ResultMetadata(BaseModel):
    status: ExecutionStatus = Field(description="Execution state for this request.")
    executed_at: datetime = Field(description="UTC timestamp when execution finished.")
    execution_mode: str = Field(default="synchronous", description="Reserved for future async use.")
    result_id: str = Field(description="Stable identifier for this result envelope.")

    @classmethod
    def completed(cls, result_id: str) -> "ResultMetadata":
        return cls(
            status=ExecutionStatus.COMPLETED,
            executed_at=datetime.now(UTC),
            result_id=result_id,
        )

    @classmethod
    def failed(cls, result_id: str) -> "ResultMetadata":
        return cls(
            status=ExecutionStatus.FAILED,
            executed_at=datetime.now(UTC),
            result_id=result_id,
        )
