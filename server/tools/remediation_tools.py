"""Remediation tools — call CC API to identify gaps and generate corrective docs."""

from typing import Any, cast

from google.adk.tools import ToolContext
from server.tools.cc_client import cc_request

JsonDict = dict[str, Any]


def _extract_controls(payload: JsonDict) -> list[JsonDict]:
    """Return control assessments as a typed list of dictionaries."""
    controls_raw_obj: object = payload.get("controlAssessments")
    if not isinstance(controls_raw_obj, list):
        return []
    controls_raw = cast(list[object], controls_raw_obj)

    controls: list[JsonDict] = []
    for item in controls_raw:
        if isinstance(item, dict):
            controls.append(cast(JsonDict, item))
    return controls


async def get_failed_controls(assessment_id: str, tool_context: ToolContext) -> JsonDict:
    """Get all failed controls from an assessment that need remediation.

    Args:
        assessment_id: The assessment to check.
        tool_context: Tool context containing user authentication.

    Returns:
        List of failed controls with IDs, titles, and reasons.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    data: JsonDict = await cc_request("GET", f"/api/assessments/{assessment_id}", token=token)
    controls = _extract_controls(data)

    failed_controls: list[JsonDict] = [
        {
            "id": c.get("controlId"),
            "title": c.get("title"),
            "reasoning": c.get("reasoning"),
            "recommendation": c.get("recommendation"),
        }
        for c in controls
        if c.get("verdict") == "Fail"
    ]

    return {
        "failed_controls": failed_controls
    }


async def list_evidence_templates(tool_context: ToolContext) -> JsonDict:
    """List available evidence/policy templates for remediation.

    Args:
        tool_context: Tool context containing user authentication.

    Returns:
        List of evidence templates.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request("GET", "/api/remediate/generate", token=token)
