import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api import ws_router, rest_router


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

app = FastAPI(
    title="Krep Voice Agent",
    description="Real-time voice assistant for compliance assessments using Gemini Live API",
    version="0.1.0",
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
