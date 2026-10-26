from fastapi import APIRouter, Depends
from ollama import embed
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chunk
from app.schemas import (
    HybridSearchHit,
    HybridSearchResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.tracing import tracer


router = APIRouter(tags=["search"])

RRF_K = 60
CANDIDATE_LIMIT = 20
RESULT_LIMIT = 5
MIN_VECTOR_DISTANCE = 0.5


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("retrieval.embed_query") as span:
        span.set_attribute("embedding.model", "nomic-embed-text")
        query_vector = embed(
            model="nomic-embed-text",
            input=payload.query,
        ).embeddings[0]

    distance = Chunk.embedding.cosine_distance(query_vector).label("distance")
    statement = (
        select(Chunk, distance)
        .where(
            Chunk.tenant_id == payload.tenant_id,
            Chunk.embedding.is_not(None),
            distance <= MIN_VECTOR_DISTANCE,
        )
        .order_by(distance)
        .limit(5)
    )

    with tracer.start_as_current_span("retrieval.vector_search") as span:
        rows = db.execute(statement).all()
        span.set_attribute("retrieval.result_count", len(rows))

    return SearchResponse(
        results=[
            SearchHit(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=float(1 - distance_value),
            )
            for chunk, distance_value in rows
        ]
    )


@router.post("/hybrid-search", response_model=HybridSearchResponse)
def hybrid_search(payload: SearchRequest, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("retrieval.embed_query") as span:
        span.set_attribute("embedding.model", "nomic-embed-text")
        query_vector = embed(
            model="nomic-embed-text",
            input=payload.query,
        ).embeddings[0]

    vector_distance = Chunk.embedding.cosine_distance(query_vector)
    vector_statement = (
        select(Chunk, vector_distance.label("distance"))
        .where(
            Chunk.tenant_id == payload.tenant_id,
            Chunk.embedding.is_not(None),
            vector_distance <= MIN_VECTOR_DISTANCE,
        )
        .order_by(vector_distance)
        .limit(CANDIDATE_LIMIT)
    )

    with tracer.start_as_current_span("retrieval.vector_search") as span:
        vector_rows = db.execute(vector_statement).all()
        span.set_attribute("retrieval.result_count", len(vector_rows))

    text_query = func.plainto_tsquery("english", payload.query)
    text_rank = func.ts_rank(Chunk.search_vector, text_query)
    text_statement = (
        select(Chunk, text_rank.label("text_rank"))
        .where(
            Chunk.tenant_id == payload.tenant_id,
            Chunk.search_vector.op("@@")(text_query),
        )
        .order_by(text_rank.desc())
        .limit(CANDIDATE_LIMIT)
    )

    with tracer.start_as_current_span("retrieval.full_text_search") as span:
        text_rows = db.execute(text_statement).all()
        span.set_attribute("retrieval.result_count", len(text_rows))

    chunks_by_id = {}
    vector_ranks = {}
    text_ranks = {}
    rrf_scores = {}

    for rank, (chunk, _distance) in enumerate(vector_rows, start=1):
        chunks_by_id[chunk.chunk_id] = chunk
        vector_ranks[chunk.chunk_id] = rank
        rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + (
            1 / (RRF_K + rank)
        )

    for rank, (chunk, _text_score) in enumerate(text_rows, start=1):
        chunks_by_id[chunk.chunk_id] = chunk
        text_ranks[chunk.chunk_id] = rank
        rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + (
            1 / (RRF_K + rank)
        )

    ranked_ids = sorted(
        rrf_scores,
        key=rrf_scores.get,
        reverse=True,
    )[:RESULT_LIMIT]

    return HybridSearchResponse(
        results=[
            HybridSearchHit(
                chunk_id=chunks_by_id[chunk_id].chunk_id,
                document_id=chunks_by_id[chunk_id].document_id,
                chunk_index=chunks_by_id[chunk_id].chunk_index,
                content=chunks_by_id[chunk_id].content,
                vector_rank=vector_ranks.get(chunk_id),
                text_rank=text_ranks.get(chunk_id),
                rrf_score=rrf_scores[chunk_id],
            )
            for chunk_id in ranked_ids
        ]
    )