"""Restful router to invoke compliance router agent for non-voice interactions."""
from typing import Annotated
from fastapi import Header, HTTPException
from google.adk import Runner
from google.genai import types
from google.adk.sessions import Session
from server.agents import compliance_router
from google.adk.sessions import InMemorySessionService
from fastapi import APIRouter

session_service = InMemorySessionService()
router = APIRouter()

runner = Runner(
    agent=compliance_router, 
    app_name="compliance_app", 
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
    
    session.state["user_token"] = authorization 

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

