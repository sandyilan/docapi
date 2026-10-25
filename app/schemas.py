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

class SearchRequest(BaseModel):
    tenant_id: int = Field(gt=0)
    query: str = Field(min_length=1, max_length=2000)


class SearchHit(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchHit]

class AskRequest(BaseModel):
    tenant_id: int = Field(gt=0)
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchHit]
    conversation_id: int

class ConversationOut(BaseModel):
    conversation_id: int
    title: str
    messages: list[dict[str, str]]
    created_at: datetime
    updated_at: datetime

class ConversationSummary(BaseModel):
    conversation_id: int
    title: str
    created_at: datetime
    updated_at: datetime

class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)

class DocumentUploadOut(DocumentOut):
    chunks_created: int

class ChunkOut(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    has_embedding: bool

class HybridSearchHit(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    vector_rank: int | None
    text_rank: int | None
    rrf_score: float


class HybridSearchResponse(BaseModel):
    results: list[HybridSearchHit]
