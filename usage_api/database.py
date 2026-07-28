from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from prisma import Prisma

from usage_api.config import Settings
from usage_api.schemas import TimeBucket, TopRequestOrder

MAX_LIMIT = 500
DEFAULT_LIMIT = 100


@dataclass
class UsageFilters:
    start: datetime | None = None
    end: datetime | None = None
    model: str | None = None
    model_group: str | None = None
    user: str | None = None
    team_id: str | None = None


@dataclass
class QueryBuilder:
    clauses: list[str] = field(default_factory=list)
    args: list[Any] = field(default_factory=list)

    def add(self, clause_template: str, value: Any) -> None:
        self.args.append(value)
        self.clauses.append(clause_template.format(param=f"${len(self.args)}"))

    def where_sql(self) -> str:
        if not self.clauses:
            return ""
        return "WHERE " + " AND ".join(self.clauses)


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def build_filters(filters: UsageFilters) -> QueryBuilder:
    builder = QueryBuilder()
    if filters.start is not None:
        builder.add('"startTime" >= {param}', filters.start)
    if filters.end is not None:
        builder.add('"startTime" < {param}', filters.end)
    if filters.model:
        builder.add("model = {param}", filters.model)
    if filters.model_group:
        builder.add("model_group = {param}", filters.model_group)
    if filters.user:
        builder.add('"user" = {param}', filters.user)
    if filters.team_id:
        builder.add("team_id = {param}", filters.team_id)
    return builder


class UsageRepository:
    def __init__(self, client: Prisma) -> None:
        self.client = client

    async def health(self) -> bool:
        result = await self.client.query_first("SELECT 1 AS ok")
        return bool(result and result.get("ok") == 1)

    async def summary(self, filters: UsageFilters) -> dict[str, Any]:
        query = build_filters(filters)
        row = await self.client.query_first(
            f"""
            SELECT
              COUNT(*)::int AS request_count,
              COALESCE(SUM(spend), 0)::float AS total_spend,
              COALESCE(SUM(prompt_tokens), 0)::bigint AS prompt_tokens,
              COALESCE(SUM(completion_tokens), 0)::bigint AS completion_tokens,
              COALESCE(SUM(total_tokens), 0)::bigint AS total_tokens
            FROM "LiteLLM_SpendLogs"
            {query.where_sql()}
            """,
            *query.args,
        )
        return row or {}

    async def timeseries(
        self, filters: UsageFilters, bucket: TimeBucket, limit: int
    ) -> list[dict[str, Any]]:
        query = build_filters(filters)
        limit = clamp_limit(limit)
        bucket_sql = {
            TimeBucket.day: "DATE_TRUNC('day', \"startTime\")",
            TimeBucket.hour: "DATE_TRUNC('hour', \"startTime\")",
        }[bucket]
        query.args.append(limit)
        return await self.client.query_raw(
            f"""
            SELECT
              {bucket_sql} AS bucket,
              COUNT(*)::int AS request_count,
              COALESCE(SUM(spend), 0)::float AS total_spend,
              COALESCE(SUM(prompt_tokens), 0)::bigint AS prompt_tokens,
              COALESCE(SUM(completion_tokens), 0)::bigint AS completion_tokens,
              COALESCE(SUM(total_tokens), 0)::bigint AS total_tokens
            FROM "LiteLLM_SpendLogs"
            {query.where_sql()}
            GROUP BY bucket
            ORDER BY bucket DESC
            LIMIT ${len(query.args)}
            """,
            *query.args,
        )

    async def model_usage(self, filters: UsageFilters, limit: int) -> list[dict[str, Any]]:
        query = build_filters(filters)
        query.args.append(clamp_limit(limit))
        return await self.client.query_raw(
            f"""
            SELECT
              model,
              model_group,
              COUNT(*)::int AS request_count,
              COALESCE(SUM(spend), 0)::float AS total_spend,
              COALESCE(SUM(prompt_tokens), 0)::bigint AS prompt_tokens,
              COALESCE(SUM(completion_tokens), 0)::bigint AS completion_tokens,
              COALESCE(SUM(total_tokens), 0)::bigint AS total_tokens,
              AVG(EXTRACT(EPOCH FROM ("endTime" - "startTime")))::float AS avg_latency_seconds
            FROM "LiteLLM_SpendLogs"
            {query.where_sql()}
            GROUP BY model, model_group
            ORDER BY total_spend DESC, total_tokens DESC
            LIMIT ${len(query.args)}
            """,
            *query.args,
        )

    async def entity_usage(
        self,
        filters: UsageFilters,
        entity: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        entity_sql = {"user": '"user"', "team_id": "team_id"}[entity]
        query = build_filters(filters)
        query.args.append(clamp_limit(limit))
        return await self.client.query_raw(
            f"""
            SELECT
              {entity_sql} AS name,
              COUNT(*)::int AS request_count,
              COALESCE(SUM(spend), 0)::float AS total_spend,
              COALESCE(SUM(prompt_tokens), 0)::bigint AS prompt_tokens,
              COALESCE(SUM(completion_tokens), 0)::bigint AS completion_tokens,
              COALESCE(SUM(total_tokens), 0)::bigint AS total_tokens
            FROM "LiteLLM_SpendLogs"
            {query.where_sql()}
            GROUP BY {entity_sql}
            ORDER BY total_spend DESC, total_tokens DESC
            LIMIT ${len(query.args)}
            """,
            *query.args,
        )

    async def requests(
        self,
        filters: UsageFilters,
        limit: int,
        order_by: TopRequestOrder | None = None,
    ) -> list[dict[str, Any]]:
        query = build_filters(filters)
        query.args.append(clamp_limit(limit))
        order_sql = {
            None: '"startTime" DESC',
            TopRequestOrder.spend: "spend DESC NULLS LAST",
            TopRequestOrder.total_tokens: "total_tokens DESC NULLS LAST",
            TopRequestOrder.latency_seconds: "latency_seconds DESC NULLS LAST",
        }[order_by]
        return await self.client.query_raw(
            f"""
            SELECT
              request_id,
              "startTime" AS start_time,
              "endTime" AS end_time,
              model,
              model_group,
              "user",
              end_user,
              team_id,
              CASE
                WHEN api_key IS NULL OR api_key = '' THEN NULL
                WHEN LENGTH(api_key) <= 8 THEN api_key
                ELSE LEFT(api_key, 8) || '...'
              END AS api_key_prefix,
              COALESCE(spend, 0)::float AS spend,
              COALESCE(prompt_tokens, 0)::bigint AS prompt_tokens,
              COALESCE(completion_tokens, 0)::bigint AS completion_tokens,
              COALESCE(total_tokens, 0)::bigint AS total_tokens,
              EXTRACT(EPOCH FROM ("endTime" - "startTime"))::float AS latency_seconds
            FROM "LiteLLM_SpendLogs"
            {query.where_sql()}
            ORDER BY {order_sql}
            LIMIT ${len(query.args)}
            """,
            *query.args,
        )


async def create_client(settings: Settings) -> Prisma:
    if not settings.database_enabled:
        raise RuntimeError("LiteLLM database is disabled.")
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")

    client = Prisma(datasource={"url": settings.database_url})
    await client.connect()
    return client
