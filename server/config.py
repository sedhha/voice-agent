from pydantic_settings import BaseSettings

USE_AUDIO = True

class Settings(BaseSettings):
    """Voice agent configuration — loaded from environment variables."""

    google_api_key: str = ""
    cc_api_url: str = "https://krep.vercel.app"
    port: int = 8080
    app_name: str = "cc-voice-agent"

    # Gemini Live API model
    gemini_model: str = "gemini-2.5-flash-native-audio-latest" if USE_AUDIO else "gemini-2.5-flash-lite"

    # Voice config
    voice_name: str = "Kore"
    silence_duration_ms: int = 1000  # Tuned up from 700 — prevents mid-sentence cutoffs

    # Phase 5: Transcript filter — ratio of Latin chars required before tagging
    # as low-confidence.  Lowered from 0.5 to reduce false drops for accented speech.
    min_latin_ratio: float = 0.3

    # Phase 7: Session TTL — sessions older than this are swept from memory
    session_ttl_seconds: int = 3600  # 1 hour

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# ADK/genai reads GOOGLE_API_KEY from os.environ directly,
# so we must ensure the .env value is exported there.
if settings.google_api_key:
    import os

    os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
