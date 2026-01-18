"""Configuration settings for Cortex backend."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    db_path: Path = Path.home() / ".cortex" / "cortex.db"

    # Server
    host: str = "127.0.0.1"
    port: int = 8742

    # AI Provider
    ai_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    chat_model: str = "llama3.2:3b"

    # Processing
    max_concurrent_processing: int = 2
    chunk_size: int = 500
    chunk_overlap: int = 50

    model_config = {"env_prefix": "CORTEX_"}


settings = Settings()
