"""Suggestion tools — provide contextual next-action chips to the user's UI."""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

JsonDict = dict[str, Any]

# Per-session queue of suggestion payloads.
# The WebSocket downstream loop drains this after each ADK event.
suggestion_queues: dict[str, asyncio.Queue[dict]] = defaultdict(asyncio.Queue)


async def suggest_next_actions(
    suggestions_json: str,
    tool_context: ToolContext,
) -> JsonDict:
    """Send contextual next-action suggestions to the user's UI as clickable chips.

    ALWAYS call this after answering a question or completing an action so the
    user can quickly continue without having to think of what to say next.

    Args:
        suggestions_json: A JSON string encoding a list of 2-4 suggestion
            objects, each with keys:
            - "label": Short display text (e.g. "View assessment results")
            - "type": One of "navigate", "query", or "action"
            - "prompt": The full text to send when the user taps this chip
            Example: '[{"label":"Show products","type":"query","prompt":"List my products"}]'
        tool_context: ADK tool context (provides session ID for routing).

    Returns:
        Confirmation dict with success status.
    """
    try:
        suggestions = json.loads(suggestions_json)
    except (json.JSONDecodeError, TypeError):
        logger.warning("suggest_next_actions received invalid JSON: %s", suggestions_json)
        return {"success": False, "error": "Invalid JSON in suggestions_json"}

    if not isinstance(suggestions, list):
        return {"success": False, "error": "suggestions_json must be a JSON array"}

    session_id = tool_context.session.id

    payload = {
        "type": "suggestions",
        "suggestions": [
            {
                "id": f"sug-{i}",
                "label": s.get("label", ""),
                "type": s.get("type", "query"),
                "prompt": s.get("prompt", s.get("label", "")),
            }
            for i, s in enumerate(suggestions)
            if isinstance(s, dict)
        ],
    }

    await suggestion_queues[session_id].put(payload)
    return {"success": True, "message": f"Sent {len(payload['suggestions'])} suggestions to UI."}
