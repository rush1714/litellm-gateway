from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from usage_api.database import DEFAULT_LIMIT, MAX_LIMIT, UsageFilters, UsageRepository
from usage_api.schemas import (
    EntityUsage,
    HealthResponse,
    ModelUsage,
    RequestRecord,
    TimeBucket,
    TimeSeriesPoint,
    TopRequestOrder,
    UsageSummary,
)

router = APIRouter()

LimitParam = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
TimeParam = Annotated[datetime | None, Query()]
OptionalStringParam = Annotated[str | None, Query(min_length=1)]


def get_repository(request: Request) -> UsageRepository:
    repository = getattr(request.app.state, "usage_repository", None)
    if repository is None:
        detail = getattr(request.app.state, "usage_startup_error", None) or "database unavailable"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    return repository


def usage_filters(
    start: TimeParam = None,
    end: TimeParam = None,
    model: OptionalStringParam = None,
    model_group: OptionalStringParam = None,
    user: OptionalStringParam = None,
    team_id: OptionalStringParam = None,
) -> UsageFilters:
    if start is not None and end is not None and start >= end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start must be earlier than end",
        )
    return UsageFilters(
        start=start,
        end=end,
        model=model,
        model_group=model_group,
        user=user,
        team_id=team_id,
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.usage_settings
    repository = getattr(request.app.state, "usage_repository", None)
    startup_error = getattr(request.app.state, "usage_startup_error", None)

    if repository is None:
        return HealthResponse(
            status="unhealthy",
            database_enabled=settings.database_enabled,
            database_connected=False,
            detail=startup_error,
        )

    try:
        connected = await repository.health()
    except Exception as exc:  # noqa: BLE001 - health should surface database failure details
        return HealthResponse(
            status="unhealthy",
            database_enabled=settings.database_enabled,
            database_connected=False,
            detail=str(exc),
        )

    return HealthResponse(
        status="ok" if connected else "unhealthy",
        database_enabled=settings.database_enabled,
        database_connected=connected,
    )


@router.get("/api/usage/summary", response_model=UsageSummary)
async def usage_summary(
    request: Request,
    filters: Annotated[UsageFilters, Depends(usage_filters)],
) -> UsageSummary:
    row = await get_repository(request).summary(filters)
    return UsageSummary(**row)


@router.get("/api/usage/timeseries", response_model=list[TimeSeriesPoint])
async def usage_timeseries(
    request: Request,
    filters: Annotated[UsageFilters, Depends(usage_filters)],
    bucket: TimeBucket = TimeBucket.day,
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[TimeSeriesPoint]:
    rows = await get_repository(request).timeseries(filters, bucket=bucket, limit=limit)
    return [TimeSeriesPoint(**row) for row in rows]


@router.get("/api/usage/models", response_model=list[ModelUsage])
async def usage_models(
    request: Request,
    filters: Annotated[UsageFilters, Depends(usage_filters)],
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[ModelUsage]:
    rows = await get_repository(request).model_usage(filters, limit=limit)
    return [ModelUsage(**row) for row in rows]


@router.get("/api/usage/users", response_model=list[EntityUsage])
async def usage_users(
    request: Request,
    filters: Annotated[UsageFilters, Depends(usage_filters)],
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[EntityUsage]:
    rows = await get_repository(request).entity_usage(filters, entity="user", limit=limit)
    return [EntityUsage(**row) for row in rows]


@router.get("/api/usage/teams", response_model=list[EntityUsage])
async def usage_teams(
    request: Request,
    filters: Annotated[UsageFilters, Depends(usage_filters)],
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[EntityUsage]:
    rows = await get_repository(request).entity_usage(filters, entity="team_id", limit=limit)
    return [EntityUsage(**row) for row in rows]


@router.get("/api/usage/top-requests", response_model=list[RequestRecord])
async def top_requests(
    request: Request,
    filters: Annotated[UsageFilters, Depends(usage_filters)],
    order_by: TopRequestOrder = TopRequestOrder.spend,
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[RequestRecord]:
    rows = await get_repository(request).requests(filters, limit=limit, order_by=order_by)
    return [RequestRecord(**row) for row in rows]


@router.get("/api/usage/recent-requests", response_model=list[RequestRecord])
async def recent_requests(
    request: Request,
    filters: Annotated[UsageFilters, Depends(usage_filters)],
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[RequestRecord]:
    rows = await get_repository(request).requests(filters, limit=limit)
    return [RequestRecord(**row) for row in rows]
