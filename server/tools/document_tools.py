"""Document tools — call CC API to list, search, and manage compliance documents."""
from typing import Any

from google.adk.tools import ToolContext
from server.tools.cc_client import cc_request

JsonDict = dict[str, Any]


async def list_documents(product_id: str, tool_context: ToolContext) -> JsonDict:
    """List all documents uploaded to a product.

    Args:
        product_id: The product to list documents for.
        tool_context: Tool context containing user authentication.

    Returns:
        List of documents with name, type, status, and upload date.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request(
        "GET", f"/api/products/{product_id}/documents", token=token
    )


async def get_document_content(
    product_id: str, document_id: str, tool_context: ToolContext
) -> JsonDict:
    """Get the text content of a specific document.

    Args:
        product_id: The product the document belongs to.
        document_id: The document ID.
        tool_context: Tool context containing user authentication.

    Returns:
        Document text content.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request(
        "GET",
        f"/api/products/{product_id}/documents/{document_id}/content",
        token=token,
    )


async def list_products(org_id: str, tool_context: ToolContext) -> JsonDict:
    """List all products/projects in an organisation.

    Args:
        org_id: The organisation ID.
        tool_context: Tool context containing user authentication.

    Returns:
        List of products with names and IDs.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request(
        "GET", "/api/products", params={"orgId": org_id}, token=token
    )


async def get_products(
    tool_context: ToolContext, org_id: str | None = None
) -> JsonDict:
    """Fetch all products accessible to the authenticated user.

    Use this when the user asks about their products, projects, or wants to
    know what they have set up.  No arguments are required — it returns
    products across all organisations the user has access to.  Optionally
    pass org_id to filter to a single organisation.

    Args:
        tool_context: Tool context containing user authentication.
        org_id: Optional organisation ID to filter products.

    Returns:
        List of products with name, description, status, assessmentsCount,
        policiesCount, and latestAssessmentScore.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    params: dict[str, str] = {}
    if org_id:
        params["organisationId"] = org_id
    return await cc_request("GET", "/api/products", params=params, token=token)


async def get_product_details(
    product_id: str, tool_context: ToolContext
) -> JsonDict:
    """Get detailed information about a specific product.

    Use this when the user asks about a specific product by name or ID, or
    when you need to drill into a product discovered via get_products().

    Args:
        product_id: The product UUID.
        tool_context: Tool context containing user authentication.

    Returns:
        Product details including name, description, status,
        assessmentsCount, policiesCount, and latestAssessmentScore.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request(
        "GET", f"/api/products/{product_id}", token=token
    )


async def list_organisations(tool_context: ToolContext) -> JsonDict:
    """List organisations the user belongs to.

    Args:
        tool_context: Tool context containing user authentication.

    Returns:
        List of organisations with IDs and names.
    """
    token = str(tool_context.session.state.get("user_token", ""))
    return await cc_request("GET", "/api/organisations", token=token)
