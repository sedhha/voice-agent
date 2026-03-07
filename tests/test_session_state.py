import sys
import uuid
from pathlib import Path

import pytest
from google.adk.sessions import InMemorySessionService

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.config import settings
from server.session_state import get_stored_session, persist_session_value


@pytest.mark.asyncio
async def test_persist_session_value_updates_stored_session() -> None:
    session_service = InMemorySessionService()
    user_id = f"user-{uuid.uuid4()}"
    session_id = f"session-{uuid.uuid4()}"

    await session_service.create_session(
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    stored = persist_session_value(
        session_service=session_service,
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
        key="user_token",
        value="firebase-token",
    )

    session = await session_service.get_session(
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    raw_session = get_stored_session(
        session_service=session_service,
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    assert stored is True
    assert raw_session is not None
    assert raw_session.state["user_token"] == "firebase-token"
    assert session is not None
    assert session.state["user_token"] == "firebase-token"
