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
    silence_duration_ms: int = 700

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# ADK/genai reads GOOGLE_API_KEY from os.environ directly,
# so we must ensure the .env value is exported there.
if settings.google_api_key:
    import os

    os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
