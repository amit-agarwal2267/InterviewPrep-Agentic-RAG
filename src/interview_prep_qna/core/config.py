from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: SecretStr
    database_host: str | None = None
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    mongodb_uri: SecretStr = SecretStr("mongodb://localhost:27017")
    mongodb_database: str = "interview_prep_qna"
    mongodb_server_selection_timeout_ms: int = 2_000
    log_level: str = "INFO"
    log_json: bool = True
    github_webhook_secret: SecretStr
    github_token: SecretStr
    github_sync_extensions: str = ".md,.markdown"
    github_max_file_bytes: int = 1_000_000
    github_live_max_results: int = 5
    notion_token: SecretStr
    sheets_shared_secret: SecretStr
    admin_trigger_secret: SecretStr | None = None
    google_service_account_path: Path
    google_spreadsheet_id: str | None = None
    google_sheet_gid: int | None = None
    google_sheet_range: str = "Sheet1!A1:Z1000"
    google_genai_api_key: SecretStr
    google_genai_embedding_model: str = "models/gemini-embedding-001"
    google_genai_embedding_cost_per_million_tokens: float | None = None
    gemini_reasoning_model: str = "gemini-3.5-flash"
    gemini_fallback_reasoning_model: str = "gemini-3.6-flash"
    answer_min_words: int = 600
    answer_max_words: int = 900
    google_flash_model: str = "gemini-3.5-flash-lite"
    google_fallback_flash_model: str = "gemini-3.1-flash-lite"
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-20b"
    tavily_api_key: SecretStr | None = None
    tavily_max_results: int = 5
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    langfuse_environment: str = "development"
    langfuse_enabled: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
