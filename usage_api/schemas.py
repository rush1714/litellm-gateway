from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TimeBucket(StrEnum):
    day = "day"
    hour = "hour"


class TopRequestOrder(StrEnum):
    spend = "spend"
    total_tokens = "total_tokens"
    latency_seconds = "latency_seconds"


class HealthResponse(BaseModel):
    status: str
    database_enabled: bool
    database_connected: bool
    detail: str | None = None


class UsageSummary(BaseModel):
    request_count: int = 0
    total_spend: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class TimeSeriesPoint(UsageSummary):
    bucket: datetime


class ModelUsage(UsageSummary):
    model: str | None = None
    model_group: str | None = None
    avg_latency_seconds: float | None = None


class EntityUsage(UsageSummary):
    name: str | None = None


class RequestRecord(BaseModel):
    request_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    model: str | None = None
    model_group: str | None = None
    user: str | None = None
    end_user: str | None = None
    team_id: str | None = None
    api_key_prefix: str | None = None
    spend: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_seconds: float | None = Field(default=None, ge=0)
