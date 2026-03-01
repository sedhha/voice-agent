import os

from fastapi import FastAPI
#
app = FastAPI(
    title="Compliance Copilot Voice Agent",
    description="Real-time voice assistant for compliance assessments using Gemini Live API",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "ok"}
