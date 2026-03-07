"""Helpers for mutating persisted state in the in-memory ADK session store."""

import time
from typing import Any

from google.adk.sessions import InMemorySessionService, Session


def get_stored_session(
    *,
    session_service: InMemorySessionService,
    app_name: str,
    user_id: str,
    session_id: str,
) -> Session | None:
    """Return the actual stored session object, not the defensive copy from get_session()."""
    return (
        session_service.sessions
        .get(app_name, {})
        .get(user_id, {})
        .get(session_id)
    )


def persist_session_value(
    *,
    session_service: InMemorySessionService,
    app_name: str,
    user_id: str,
    session_id: str,
    key: str,
    value: Any,
) -> bool:
    """Persist a session-scoped value into the in-memory storage session."""
    session = get_stored_session(
        session_service=session_service,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        return False

    session.state[key] = value
    session.last_update_time = time.time()
    return True
