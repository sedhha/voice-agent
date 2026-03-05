"""Assessment tools — call CC API to list, run, and summarise assessments."""

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


async def list_assessments(product_id: str, tool_context: ToolContext) -> JsonDict:
    """List all compliance assessments for a product.

    Args:
        product_id: The product ID to list assessments for.
        tool_context: Tool context containing user authentication.

    Returns:
        List of assessments with framework, status, and scores.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request(
        "GET", "/api/assessments", params={"productId": product_id}, token=token
    )


async def get_assessment(assessment_id: str, tool_context: ToolContext) -> JsonDict:
    """Get a single assessment including control results when completed.

    Args:
        assessment_id: The assessment ID.
        tool_context: Tool context containing user authentication.

    Returns:
        Assessment details with control assessments.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request("GET", f"/api/assessments/{assessment_id}", token=token)


async def get_compliance_summary(
    assessment_id: str, tool_context: ToolContext
) -> JsonDict:
    """Get a summary of compliance results — pass/fail counts and critical gaps.

    Args:
        assessment_id: The assessment to summarise.
        tool_context: Tool context containing user authentication.

    Returns:
        Summary with total controls, passed, failed, partial counts,
        and list of critical gaps.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    data: JsonDict = await cc_request("GET", f"/api/assessments/{assessment_id}", token=token)
    controls = _extract_controls(data)
    passed = sum(1 for c in controls if c.get("verdict") == "Pass")
    failed = sum(1 for c in controls if c.get("verdict") == "Fail")
    partial = sum(1 for c in controls if c.get("verdict") == "Partial")
    critical_gaps: list[JsonDict] = [
        {
            "control": c.get("controlId"),
            "title": c.get("title"),
            "reason": c.get("reasoning"),
        }
        for c in controls
        if c.get("verdict") == "Fail"
    ][:5]
    return {
        "total": len(controls),
        "passed": passed,
        "failed": failed,
        "partial": partial,
        "score": f"{passed}/{len(controls)}" if controls else "0/0",
        "critical_gaps": critical_gaps,
    }


async def list_frameworks(tool_context: ToolContext) -> JsonDict:
    """List available compliance frameworks (SOC 2, GDPR, HIPAA, etc.).

    Args:
        tool_context: Tool context containing user authentication.

    Returns:
        List of frameworks with IDs and names.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request("GET", "/api/frameworks", token=token)
