from __future__ import annotations

from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str | None = Field(default=None, min_length=100, max_length=50000)
    url: AnyHttpUrl | None = None
    include_detailed_summary: bool = False

    @model_validator(mode="after")
    def validate_input(self) -> "AnalyzeRequest":
        if not self.text and not self.url:
            raise ValueError("Either text or url must be provided")
        return self


class AnalyzeAcceptedResponse(BaseModel):
    status: str = "accepted"
    job_id: UUID
    article_id: UUID


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    article_id: UUID
    include_detailed_summary: bool = False


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    classification: str | None = None
    confidence: float | None = None
    processing_ms: int | None = None
    error_message: str | None = None


class ArticleResponse(BaseModel):
    article_id: UUID
    source_url: str | None
    title: str | None
    raw_text: str
    cleaned_text: str
    metadata: dict
    latest_job: dict | None
