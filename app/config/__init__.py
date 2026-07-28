from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None
    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX_NAME: str | None = None
    ELEVENLABS_API_KEY: str | None = None
    ELEVENLABS_VOICE_ID: str | None = None
    ELEVENLABS_MODEL: str | None = None
    GROQ_API_KEY: str | None = None
    LLM_PROVIDER: str = "openai"
    OPENROUTER_API_KEY: str | None = None

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    RESEND_API_KEY: str | None = None
    MAIL_FROM_ADDRESS: str = "noreply@aiinterviewagent.com"
    MAIL_FROM_NAME: str = "AI Interview Agent"
    APP_URL: str = "http://localhost:5173"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or v == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be overridden in .env — do not use the default")
        return v


settings = Settings()
