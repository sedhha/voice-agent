"""Helpers for mutating persisted state in the in-memory ADK session store."""

import logging
import time
from typing import Any

from google.adk.sessions import InMemorySessionService, Session

logger = logging.getLogger(__name__)


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


def sweep_expired_sessions(
    *,
    session_service: InMemorySessionService,
    ttl_seconds: int,
) -> int:
    """Remove sessions older than TTL from the in-memory store.

    Returns the number of sessions removed.  Called periodically by
    the background sweeper in main.py (Phase 7).
    """
    now = time.time()
    removed = 0
    for app_name, users in list(session_service.sessions.items()):
        for user_id, sessions in list(users.items()):
            expired_ids = [
                sid
                for sid, session in sessions.items()
                if (now - session.last_update_time) > ttl_seconds
            ]
            for sid in expired_ids:
                del sessions[sid]
                removed += 1
            if not sessions:
                del users[user_id]
        if not users:
            del session_service.sessions[app_name]
    if removed:
        logger.info("Swept %d expired sessions (TTL=%ds)", removed, ttl_seconds)
    return removed
