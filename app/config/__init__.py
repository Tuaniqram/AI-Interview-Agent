import json
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings.sources import EnvSettingsSource, DotEnvSettingsSource


class _LenientEnvSource(EnvSettingsSource):
    """Skip JSON decoding for CORS_ORIGINS — raw string goes to validator instead."""

    def prepare_field_value(self, field_name, field, value, value_is_complex):
        if field_name == "CORS_ORIGINS":
            return value
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class _LenientDotenvSource(DotEnvSettingsSource):
    """Same lenient behavior for .env file."""

    def prepare_field_value(self, field_name, field, value, value_is_complex):
        if field_name == "CORS_ORIGINS":
            return value
        return super().prepare_field_value(field_name, field, value, value_is_complex)


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

    RESEND_API_KEY: str | None = None
    MAIL_FROM_ADDRESS: str = "noreply@aiinterviewagent.com"
    MAIL_FROM_NAME: str = "AI Interview Agent"
    APP_URL: str = "http://localhost:5173"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Anti-cheat integrity guard (contract: docs/anti-cheat-guard.md).
    # Master switch is OFF by default so developers can keep testing with AI.
    ANTI_CHEAT_GUARD_ENABLED: bool = False
    ANTI_CHEAT_LLM_JUDGE: bool = True
    ANTI_CHEAT_FLAG_THRESHOLD: int = 70
    ANTI_CHEAT_MAX_FLAGS: int = 3
    # Hard per-answer time window surfaced in the integrity policy (0 = disabled
    # in the UI; the judge still penalizes near-instant long answers).
    ANTI_CHEAT_ANSWER_TIME_LIMIT_S: int = 120
    # Pointer-leave events that count as possible second-screen reading.
    ANTI_CHEAT_POINTER_LEAVE_THRESHOLD: int = 3
    # Wall-clock vs rAF divergence (seconds) that counts as a session-tamper gap.
    ANTI_CHEAT_TAMPER_DIVERGENCE_S: float = 0.5

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v == "*":
                return ["*"]
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",")]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("SECRET_KEY must not be empty")
        if v == "dev-secret-key-change-in-production":
            import warnings
            warnings.warn("SECRET_KEY is still the dev default — set a strong secret in production")
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (init_settings, _LenientEnvSource(settings_cls), _LenientDotenvSource(settings_cls), file_secret_settings)


settings = Settings()
