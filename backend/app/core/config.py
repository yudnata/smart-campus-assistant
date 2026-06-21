from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    project_name: str = Field(default="STKI RAG API", validation_alias="PROJECT_NAME")
    version: str = Field(default="1.0.0", validation_alias="VERSION")

    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/stki_rag",
        validation_alias="DATABASE_URL",
    )

    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias="GROQ_MODEL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
