"""Restful router to invoke compliance router agent for non-voice interactions."""
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from google.adk import Runner
from google.adk.sessions import Session
from google.adk.sessions import InMemorySessionService
from google.genai import types

from server.agents import compliance_router
from server.config import settings
from server.session_state import persist_session_value

session_service = InMemorySessionService()
router = APIRouter()

runner = Runner(
    agent=compliance_router, 
    app_name=settings.app_name, 
    session_service=session_service
)

@router.post("/text-chat")
async def invoke_agent(
    session: Session, 
    query: str,
    authorization: Annotated[str | None, Header()] = None
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = authorization.removeprefix("Bearer ").strip()
    existing_session = await session_service.get_session(
        app_name=settings.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )

    if not existing_session:
        await session_service.create_session(
            app_name=settings.app_name,
            user_id=session.user_id,
            session_id=session.id,
        )

    stored = persist_session_value(
        session_service=session_service,
        app_name=settings.app_name,
        user_id=session.user_id,
        session_id=session.id,
        key="user_token",
        value=token,
    )
    if not stored:
        raise HTTPException(status_code=500, detail="Could not persist session token")

    user_message = types.Content(
        role="user", 
        parts=[types.Part(text=query)]
    )

    try:
        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=user_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        return {"response": response_text, "session_id": session.id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
