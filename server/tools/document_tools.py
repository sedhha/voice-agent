"""Document tools — call CC API to list, search, and manage compliance documents."""

from server.tools.cc_client import cc_request


async def list_documents(product_id: str, token: str = "") -> dict:
    """List all documents uploaded to a product.

    Args:
        product_id: The product to list documents for.
        token: User auth token.

    Returns:
        List of documents with name, type, status, and upload date.
    """
    return await cc_request(
        "GET", f"/api/products/{product_id}/documents", token=token
    )


async def get_document_content(
    product_id: str, document_id: str, token: str = ""
) -> dict:
    """Get the text content of a specific document.

    Args:
        product_id: The product the document belongs to.
        document_id: The document ID.
        token: User auth token.

    Returns:
        Document text content.
    """
    return await cc_request(
        "GET",
        f"/api/products/{product_id}/documents/{document_id}/content",
        token=token,
    )


async def list_products(org_id: str, token: str = "") -> dict:
    """List all products/projects in an organisation.

    Args:
        org_id: The organisation ID.
        token: User auth token.

    Returns:
        List of products with names and IDs.
    """
    return await cc_request(
        "GET", "/api/products", params={"orgId": org_id}, token=token
    )


async def list_organisations(token: str = "") -> dict:
    """List organisations the user belongs to.

    Args:
        token: User auth token.

    Returns:
        List of organisations with IDs and names.
    """
    return await cc_request("GET", "/api/organisations", token=token)
