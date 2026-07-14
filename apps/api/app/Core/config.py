"""Application settings — validated at startup, env-swappable seams."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TIMEBOX_", env_file=".env", extra="ignore")

    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8787

    # Relational store seam: point at Postgres in production, SQLite locally.
    database_url: str = "sqlite+aiosqlite:///./data/timebox.db"

    # LLM seam — Ollama only in this prototype. Never hardcode model names.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = Field(default=120.0, le=120.0)

    session_ttl_hours: int = 12
    prompt_max_chars: int = 8000
    purge_after_days: int = 14

    mc_default_iterations: int = 2_000
    mc_max_iterations: int = 10_000
    mc_default_window_days: int = 49


settings = Settings()
