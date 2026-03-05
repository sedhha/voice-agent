from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api import ws_router, rest_router

app = FastAPI(
    title="Compliance Copilot Voice Agent",
    description="Real-time voice assistant for compliance assessments using Gemini Live API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(rest_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
