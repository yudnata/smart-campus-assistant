from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    project_name: str = "STKI RAG API"
    version: str = "1.0.0"
    
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/stki_rag")
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
