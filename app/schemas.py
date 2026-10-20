from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=10)


class DocumentOut(BaseModel):
    id: str
    title: str | None = None
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime