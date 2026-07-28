from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from usage_api.config import get_settings
from usage_api.database import UsageRepository, create_client
from usage_api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.usage_settings = settings
    app.state.usage_client = None
    app.state.usage_repository = None
    app.state.usage_startup_error = None

    try:
        client = await create_client(settings)
        app.state.usage_client = client
        app.state.usage_repository = UsageRepository(client)
    except Exception as exc:  # noqa: BLE001 - API health exposes startup details for operators
        app.state.usage_startup_error = str(exc)

    try:
        yield
    finally:
        client = getattr(app.state, "usage_client", None)
        if client is not None and client.is_connected():
            await client.disconnect()


app = FastAPI(
    title="LiteLLM Usage API",
    description="REST API for LiteLLM spend and token usage analytics.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
