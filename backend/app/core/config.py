"""
AI Research Assistant — Application Configuration

Loads and validates all environment variables at startup.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application settings loaded from environment variables.
    Validates that required values are present at startup.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────
    APP_NAME: str = "AI Research Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Database ─────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://aira_user:aira_dev_password@localhost:5432/aira_db"

    # ── Authentication ───────────────────────
    SECRET_KEY: str = "CHANGE_ME_generate_a_strong_random_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ─────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ── LLM Provider ─────────────────────────
    LLM_PROVIDER: str = "gemini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3
    LLM_MAX_TOKENS: int = 4096

    # ── Embeddings ───────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── Vector Store ─────────────────────────
    VECTOR_STORE_TYPE: str = "chroma"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION: str = "research_documents"

    # ── Document Storage ─────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = ".pdf,.txt,.md,.markdown,.docx,.csv"

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ── RAG Settings ─────────────────────────
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 5

    # ── MCP Integration ──────────────────────
    MCP_ENABLED: bool = True
    MCP_SERVERS: str = "[]"

    # ── Rate Limiting ────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── URL Fetching ─────────────────────────
    MAX_URL_FETCH_SIZE_MB: int = 10
    URL_FETCH_TIMEOUT_SECONDS: int = 30
    BLOCKED_IP_RANGES: str = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8"


settings = Settings()
