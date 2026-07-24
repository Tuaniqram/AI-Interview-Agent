from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-secret-key-change-in-production"
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

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
