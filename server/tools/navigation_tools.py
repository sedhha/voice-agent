"""Navigation tools — emit UI commands so the frontend can navigate on behalf of the user."""

import asyncio
from collections import defaultdict
from typing import Any

from google.adk.tools import ToolContext

JsonDict = dict[str, Any]

# Per-session queue of navigation commands.
# The WebSocket downstream loop drains this after each ADK event.
nav_queues: dict[str, asyncio.Queue[dict[str, str]]] = defaultdict(asyncio.Queue)


async def navigate_to_page(
    action: str,
    tool_context: ToolContext,
    org_id: str = "",
    product_id: str = "",
    assessment_id: str = "",
) -> JsonDict:
    """Navigate the Compliance Copilot UI to a specific page.

    Call this after fetching data (products, assessments, etc.) when the user
    wants to *see* something in the app.  The frontend will automatically
    route to the correct page.

    Args:
        action: One of:
            - "open_organisation" — go to the organisation dashboard
            - "open_product"      — go to a product page
            - "open_assessment"   — go to an assessment results page
        tool_context: ADK tool context (provides session ID for routing).
        org_id: Organisation UUID (required for all actions).
        product_id: Product UUID (required for open_product / open_assessment).
        assessment_id: Assessment UUID (required for open_assessment).

    Returns:
        Confirmation dict with success status.
    """
    if not org_id:
        return {"success": False, "error": "org_id is required for navigation."}

    if action in ("open_product", "open_assessment") and not product_id:
        return {"success": False, "error": "product_id is required for this action."}

    if action == "open_assessment" and not assessment_id:
        return {"success": False, "error": "assessment_id is required to open an assessment."}

    command: dict[str, str] = {
        "type": "action",
        "action": action,
        "orgId": org_id,
    }
    if product_id:
        command["productId"] = product_id
    if assessment_id:
        command["assessmentId"] = assessment_id

    session_id = tool_context.session.id
    await nav_queues[session_id].put(command)

    labels = {
        "open_organisation": "organisation dashboard",
        "open_product": "product page",
        "open_assessment": "assessment results",
    }
    destination = labels.get(action, action)
    return {"success": True, "message": f"Navigating the user to the {destination}."}
