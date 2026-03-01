"""Assessment tools — call CC API to list, run, and summarise assessments."""

from server.tools.cc_client import cc_request


async def list_assessments(product_id: str, token: str = "") -> dict:
    """List all compliance assessments for a product.

    Args:
        product_id: The product ID to list assessments for.
        token: User auth token.

    Returns:
        List of assessments with framework, status, and scores.
    """
    return await cc_request(
        "GET", "/api/assessments", params={"productId": product_id}, token=token
    )


async def get_assessment(assessment_id: str, token: str = "") -> dict:
    """Get a single assessment including control results when completed.

    Args:
        assessment_id: The assessment ID.
        token: User auth token.

    Returns:
        Assessment details with control assessments.
    """
    return await cc_request("GET", f"/api/assessments/{assessment_id}", token=token)


async def get_compliance_summary(assessment_id: str, token: str = "") -> dict:
    """Get a summary of compliance results — pass/fail counts and critical gaps.

    Args:
        assessment_id: The assessment to summarise.
        token: User auth token.

    Returns:
        Summary with total controls, passed, failed, partial counts,
        and list of critical gaps.
    """
    data = await cc_request("GET", f"/api/assessments/{assessment_id}", token=token)
    controls = data.get("controlAssessments", [])
    passed = sum(1 for c in controls if c.get("verdict") == "Pass")
    failed = sum(1 for c in controls if c.get("verdict") == "Fail")
    partial = sum(1 for c in controls if c.get("verdict") == "Partial")
    critical_gaps = [
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


async def list_frameworks(token: str = "") -> dict:
    """List available compliance frameworks (SOC 2, GDPR, HIPAA, etc.).

    Args:
        token: User auth token.

    Returns:
        List of frameworks with IDs and names.
    """
    return await cc_request("GET", "/api/frameworks", token=token)
