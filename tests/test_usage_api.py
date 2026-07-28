import os
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from usage_api.schemas import TimeBucket, TopRequestOrder


class FakeUsageRepository:
    def __init__(self) -> None:
        self.last_filters = None

    async def health(self) -> bool:
        return True

    async def summary(self, filters: Any) -> dict[str, Any]:
        self.last_filters = filters
        return {
            "request_count": 3,
            "total_spend": 1.25,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

    async def timeseries(
        self, filters: Any, bucket: TimeBucket, limit: int
    ) -> list[dict[str, Any]]:
        self.last_filters = filters
        assert bucket == TimeBucket.hour
        assert limit == 2
        return [
            {
                "bucket": datetime(2026, 7, 28, 12, tzinfo=UTC),
                "request_count": 2,
                "total_spend": 1.0,
                "prompt_tokens": 80,
                "completion_tokens": 40,
                "total_tokens": 120,
            }
        ]

    async def model_usage(self, filters: Any, limit: int) -> list[dict[str, Any]]:
        self.last_filters = filters
        assert limit == 1
        return [
            {
                "model": "claude-sonnet-5",
                "model_group": "claude",
                "request_count": 3,
                "total_spend": 1.25,
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "avg_latency_seconds": 2.5,
            }
        ]

    async def entity_usage(self, filters: Any, entity: str, limit: int) -> list[dict[str, Any]]:
        self.last_filters = filters
        assert entity in {"user", "team_id"}
        return [
            {
                "name": "frontend",
                "request_count": 3,
                "total_spend": 1.25,
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        ]

    async def requests(
        self,
        filters: Any,
        limit: int,
        order_by: TopRequestOrder | None = None,
    ) -> list[dict[str, Any]]:
        self.last_filters = filters
        assert limit <= 5
        return [
            {
                "request_id": "req-1",
                "start_time": datetime(2026, 7, 28, 12, tzinfo=UTC),
                "end_time": datetime(2026, 7, 28, 12, 0, 2, tzinfo=UTC),
                "model": "claude-sonnet-5",
                "model_group": "claude",
                "user": "alice",
                "end_user": None,
                "team_id": "frontend",
                "api_key_prefix": "sk-12345...",
                "spend": 0.5,
                "prompt_tokens": 40,
                "completion_tokens": 20,
                "total_tokens": 60,
                "latency_seconds": 2.0,
            }
        ]


def main() -> int:
    os.environ["LITELLM_ENABLE_DATABASE"] = "false"

    from usage_api.main import app

    with TestClient(app) as client:
        repository = FakeUsageRepository()
        app.state.usage_repository = repository
        app.state.usage_startup_error = None

        response = client.get("/health")
        assert response.status_code == 200, response.text
        assert response.json()["database_connected"] is True
        assert response.json()["status"] == "ok"

        response = client.get(
            "/api/usage/summary",
            params={
                "start": "2026-07-28T00:00:00Z",
                "end": "2026-07-29T00:00:00Z",
                "model": "claude-sonnet-5",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["total_tokens"] == 150
        assert repository.last_filters.model == "claude-sonnet-5"

        response = client.get("/api/usage/timeseries", params={"bucket": "hour", "limit": 2})
        assert response.status_code == 200, response.text
        assert response.json()[0]["bucket"].startswith("2026-07-28T12:00:00")

        response = client.get("/api/usage/models", params={"limit": 1})
        assert response.status_code == 200, response.text
        assert response.json()[0]["model"] == "claude-sonnet-5"

        for path in ("/api/usage/users", "/api/usage/teams"):
            response = client.get(path, params={"limit": 5})
            assert response.status_code == 200, response.text
            assert response.json()[0]["name"] == "frontend"

        response = client.get(
            "/api/usage/top-requests",
            params={"order_by": "latency_seconds", "limit": 5},
        )
        assert response.status_code == 200, response.text
        assert response.json()[0]["api_key_prefix"] == "sk-12345..."

        response = client.get("/api/usage/recent-requests", params={"limit": 5})
        assert response.status_code == 200, response.text
        assert response.json()[0]["request_id"] == "req-1"

        response = client.get(
            "/api/usage/summary",
            params={"start": "2026-07-29T00:00:00Z", "end": "2026-07-28T00:00:00Z"},
        )
        assert response.status_code == 422, response.text

        response = client.get("/api/usage/top-requests", params={"order_by": "unsafe"})
        assert response.status_code == 422, response.text

    print("usage API smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
