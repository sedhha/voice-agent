"""HTTP client for calling the Compliance Copilot REST API."""

import logging
from typing import Any

import httpx

from server.config import settings

logger = logging.getLogger(__name__)

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

    Returns the JSON response on success, or an error dict on failure
    so the LLM agent can report the issue to the user instead of crashing.
    """
    client = get_client()
    headers: dict[str, str] = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = await client.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("CC API error: %s %s → %d", method, path, e.response.status_code)
        return {
            "error": True,
            "status": e.response.status_code,
            "message": f"API returned {e.response.status_code} for {method} {path}",
        }
    except httpx.ConnectError as e:
        logger.error("CC API connection failed: %s %s → %s", method, path, e)
        return {
            "error": True,
            "message": f"Could not connect to Compliance Copilot API: {e}",
        }
