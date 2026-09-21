"""
MeetCore — Configuration
Central place for env vars, model IDs, and constants.
"""
import os
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()


class Settings:
    # --- AssemblyAI ---
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")

    # Pre-recorded transcription (async, with webhook)
    ASSEMBLYAI_BASE_URL: str = "https://api.assemblyai.com"

    # LeMUR task endpoint — confirmed from current docs
    ASSEMBLYAI_LEMUR_URL: str = "https://api.assemblyai.com/lemur/v3/generate/task"

    # LeMUR model — confirmed valid value from SDK source
    ASSEMBLYAI_LEMUR_MODEL: str = "anthropic/claude-3-5-sonnet"

    # Webhook URL — your ngrok URL + path
    # ASSEMBLYAI_WEBHOOK_URL: str = os.getenv("ASSEMBLYAI_WEBHOOK_URL", "")

    # Realtime streaming STT
    ASSEMBLYAI_STREAMING_URL: str = "wss://streaming.assemblyai.com/v3/ws"

    # --- Groq ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_REASONING_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_REASONING_EFFORT: str = "default"
    GROQ_CHAT_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_CHAT_EFFORT: str = "none"
    GROQ_TTS_MODEL: str = "canopylabs/orpheus-v1-english"

    # --- Gemini (embeddings only) ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_EMBEDDING_DIM: int = 768
    GEMINI_EMBEDDING_URL: str = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "text-embedding-004:embedContent"
    )

    # --- Supabase ---
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # --- Brevo ---
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "nio@midev.ng")
    BREVO_SENDER_NAME: str = "Nio from MeetCore"

    # --- Google Calendar ---
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")

    # --- App ---
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_AUDIO_FORMATS: tuple = (".mp4", ".mp3", ".wav", ".m4a", ".mpeg", ".mpg")
    ENV: str = os.getenv("ENV", "development")

    # --- Dev flags ---
    MOCK_LEMUR: bool = os.getenv("MOCK_LEMUR", "false").lower() == "true"
    
    # Brevo Mail Settings
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = "adetusiyan@gmail.com"
    BREVO_SENDER_NAME: str = "Nio from MeetCore"
    DEFAULT_RECIPIENT_EMAIL: str = "adetumosgad@gmail.com"

@lru_cache
def get_settings() -> Settings:
    return Settings()