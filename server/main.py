import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api import ws_router, rest_router
from server.config import settings


def configure_logging() -> None:
    """Emit application logs through a dedicated handler at INFO level."""
    server_logger = logging.getLogger("server")
    if server_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))

    server_logger.addHandler(handler)
    server_logger.setLevel(logging.INFO)
    server_logger.propagate = False


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Phase 7: Run periodic session cleanup in the background."""
    from server.api.ws import session_service
    from server.session_state import sweep_expired_sessions

    async def _session_sweeper():
        """Sweep expired sessions every 5 minutes."""
        while True:
            await asyncio.sleep(300)
            try:
                sweep_expired_sessions(
                    session_service=session_service,
                    ttl_seconds=settings.session_ttl_seconds,
                )
            except Exception:
                logger.exception("Session sweep failed")

    task = asyncio.create_task(_session_sweeper())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Krep Voice Agent",
    description="Real-time voice assistant for compliance assessments using Gemini Live API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(rest_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
