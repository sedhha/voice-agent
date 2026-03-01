"""Quick smoke test for the voice agent server.

Usage:
    uv run python scripts/test_setup.py

Tests:
    1. Health endpoint (HTTP GET)
    2. WebSocket connection + text message exchange
    3. Agent routing (sends test prompts, checks for responses)

Requires the server to be running:
    uv run uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload
"""

import asyncio
import json
import sys

import httpx
import websockets

BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080"


def log(status: str, msg: str):
    icon = {"PASS": "\033[32m✓\033[0m", "FAIL": "\033[31m✗\033[0m", "INFO": "\033[34m→\033[0m"}
    print(f"  {icon.get(status, '?')} {msg}")


async def test_health():
    """Test 1: Health endpoint."""
    print("\n[1/3] Health endpoint")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}/health")
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "ok":
                log("PASS", f"GET /health → {data}")
                return True
            else:
                log("FAIL", f"Unexpected response: {resp.status_code} {data}")
                return False
    except httpx.ConnectError:
        log("FAIL", f"Cannot connect to {BASE_URL} — is the server running?")
        return False


async def test_websocket_connect():
    """Test 2: WebSocket connection opens and stays alive."""
    print("\n[2/3] WebSocket connection")
    try:
        async with websockets.connect(
            f"{WS_URL}/ws/voice/test-user/test-session",
            open_timeout=10,
        ) as ws:
            log("PASS", "WebSocket connected to /ws/voice/test-user/test-session")

            # Send a text message
            msg = {"type": "text", "text": "Hello"}
            await ws.send(json.dumps(msg))
            log("INFO", f"Sent: {msg}")

            # Wait for any response (text or audio) with timeout
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=15)
                if isinstance(response, bytes):
                    log("PASS", f"Received audio response: {len(response)} bytes")
                else:
                    data = json.loads(response)
                    log("PASS", f"Received: {data}")
                return True
            except asyncio.TimeoutError:
                log("FAIL", "No response within 15s — check GOOGLE_API_KEY in .env")
                return False

    except (OSError, websockets.exceptions.WebSocketException) as e:
        log("FAIL", f"WebSocket connection failed: {e}")
        return False


async def test_agent_routing():
    """Test 3: Send domain-specific prompts, verify agent responds."""
    print("\n[3/3] Agent routing")

    test_prompts = [
        ("What compliance frameworks do you support?", "general"),
        ("List my assessments", "assessment"),
        ("What documents do I need for HIPAA?", "document"),
    ]

    passed = 0
    for prompt, expected_agent in test_prompts:
        try:
            async with websockets.connect(
                f"{WS_URL}/ws/voice/test-user/routing-{expected_agent}",
                open_timeout=10,
            ) as ws:
                await ws.send(json.dumps({"type": "text", "text": prompt}))
                log("INFO", f"Sent: \"{prompt}\" (expect: {expected_agent})")

                # Collect responses for a few seconds
                responses = []
                try:
                    while True:
                        resp = await asyncio.wait_for(ws.recv(), timeout=10)
                        if isinstance(resp, bytes):
                            responses.append(f"[audio: {len(resp)} bytes]")
                        else:
                            data = json.loads(resp)
                            responses.append(data)
                            # Show transcripts as they come
                            if data.get("type") in ("text", "output_transcript"):
                                log("INFO", f"  Agent: {data.get('text', '')[:120]}")
                except asyncio.TimeoutError:
                    pass

                if responses:
                    log("PASS", f"Got {len(responses)} response(s) for {expected_agent}")
                    passed += 1
                else:
                    log("FAIL", f"No response for {expected_agent}")

        except (OSError, websockets.exceptions.WebSocketException) as e:
            log("FAIL", f"Connection failed for {expected_agent}: {e}")

    return passed == len(test_prompts)


async def main():
    print("=" * 50)
    print("  Compliance Copilot Voice Agent — Smoke Test")
    print("=" * 50)

    results = []

    # Test 1: Health
    results.append(await test_health())
    if not results[0]:
        print("\n\033[31mServer not running. Start it with:\033[0m")
        print("  uv run uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload")
        sys.exit(1)

    # Test 2: WebSocket
    results.append(await test_websocket_connect())

    # Test 3: Routing (only if WS works)
    if results[1]:
        results.append(await test_agent_routing())
    else:
        print("\n[3/3] Agent routing — skipped (WebSocket failed)")
        results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 50}")
    print(f"  Results: {passed}/{total} passed")
    if passed == total:
        print("  \033[32mAll tests passed!\033[0m")
    else:
        print("  \033[33mSome tests failed — check output above.\033[0m")
    print(f"{'=' * 50}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
