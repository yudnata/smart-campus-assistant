from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(
        default=10,
        ge=1,
        le=20,
        validation_alias=AliasChoices("top_k", "topK"),
    )
    conversation_id: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class SourceResponse(BaseModel):
    id: str
    source_file: str | None = None
    doc_type: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    pages: str | None = None
    chapter: str | None = None
    section: str | None = None
    subsection: str | None = None
    section_path: str | None = None
    preview: str
    similarity: float = 0.0
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceResponse]
