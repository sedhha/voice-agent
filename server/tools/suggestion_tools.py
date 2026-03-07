"""Suggestion tools — provide contextual next-action chips to the user's UI."""

import asyncio
from collections import defaultdict
from typing import Any

from google.adk.tools import ToolContext

JsonDict = dict[str, Any]

# Per-session queue of suggestion payloads.
# The WebSocket downstream loop drains this after each ADK event.
suggestion_queues: dict[str, asyncio.Queue[dict]] = defaultdict(asyncio.Queue)


async def suggest_next_actions(
    suggestions: list[dict[str, str]],
    tool_context: ToolContext,
) -> JsonDict:
    """Send contextual next-action suggestions to the user's UI as clickable chips.

    ALWAYS call this after answering a question or completing an action so the
    user can quickly continue without having to think of what to say next.

    Args:
        suggestions: A list of 2-4 suggestion objects, each with:
            - label: Short display text (e.g. "View assessment results")
            - type: One of "navigate" (go to a page), "query" (ask a question),
              or "action" (trigger an operation)
            - prompt: The full text to send when the user taps this chip
        tool_context: ADK tool context (provides session ID for routing).

    Returns:
        Confirmation dict with success status.
    """
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
        ],
    }

    await suggestion_queues[session_id].put(payload)
    return {"success": True, "message": f"Sent {len(suggestions)} suggestions to UI."}
