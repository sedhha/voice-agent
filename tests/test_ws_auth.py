import asyncio
import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.api.ws import session_service, store_user_token, wait_for_auth
from server.config import settings


class DummyWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.closed: tuple[int | None, str | None] | None = None

    async def send_text(self, text: str) -> None:
        self.messages.append(json.loads(text))

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        self.closed = (code, reason)


@pytest.mark.asyncio
async def test_store_user_token_persists_session_state() -> None:
    user_id = f"user-{uuid.uuid4()}"
    session_id = f"session-{uuid.uuid4()}"

    await session_service.create_session(
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    stored = await store_user_token(
        user_id=user_id,
        session_id=session_id,
        token_value="firebase-token",
    )

    session = await session_service.get_session(
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    assert stored is True
    assert session is not None
    assert session.state["user_token"] == "firebase-token"


@pytest.mark.asyncio
async def test_wait_for_auth_closes_socket_on_timeout() -> None:
    websocket = DummyWebSocket()
    auth_ready = asyncio.Event()

    authenticated = await wait_for_auth(
        websocket=websocket,
        auth_ready=auth_ready,
        session_id="session-timeout",
        timeout_seconds=0.01,
    )

    assert authenticated is False
    assert websocket.messages == [
        {
            "type": "error",
            "message": "Voice agent authentication timed out. Please try again.",
        }
    ]
    assert websocket.closed == (4401, "Authentication required")


@pytest.mark.asyncio
async def test_wait_for_auth_returns_when_token_is_ready() -> None:
    websocket = DummyWebSocket()
    auth_ready = asyncio.Event()
    auth_ready.set()

    authenticated = await wait_for_auth(
        websocket=websocket,
        auth_ready=auth_ready,
        session_id="session-ready",
        timeout_seconds=0.01,
    )

    assert authenticated is True
    assert websocket.messages == []
    assert websocket.closed is None
