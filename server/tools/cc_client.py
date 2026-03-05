"""HTTP client for calling the Compliance Copilot REST API."""

from typing import Any

import httpx

from server.config import settings

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return a shared async HTTP client for CC API calls."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.cc_api_url,
            timeout=30.0,
        )
    return _client


async def cc_request(
    method: str,
    path: str,
    *,
    token: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Make an authenticated request to the Compliance Copilot API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g. /api/products)
        token: Firebase auth token for the user session
        **kwargs: Passed to httpx (json, params, etc.)
    """
    client = get_client()
    headers: dict[str, str] = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = await client.request(method, path, headers=headers, **kwargs)
    response.raise_for_status()
    return response.json()
