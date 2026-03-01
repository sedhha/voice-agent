"""Remediation tools — call CC API to identify gaps and generate corrective docs."""

from server.tools.cc_client import cc_request


async def get_failed_controls(assessment_id: str, token: str = "") -> dict:
    """Get all failed controls from an assessment that need remediation.

    Args:
        assessment_id: The assessment to check.
        token: User auth token.

    Returns:
        List of failed controls with IDs, titles, and reasons.
    """
    data = await cc_request("GET", f"/api/assessments/{assessment_id}", token=token)
    return {
        "failed_controls": [
            {
                "id": c.get("controlId"),
                "title": c.get("title"),
                "reasoning": c.get("reasoning"),
                "recommendation": c.get("recommendation"),
            }
            for c in data.get("controlAssessments", [])
            if c.get("verdict") == "Fail"
        ]
    }


async def list_evidence_templates(token: str = "") -> dict:
    """List available evidence/policy templates for remediation.

    Args:
        token: User auth token.

    Returns:
        List of evidence templates.
    """
    return await cc_request("GET", "/api/remediate/generate", token=token)
