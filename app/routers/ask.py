import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from ollama import chat, embed
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chunk, Conversation
from app.schemas import AskRequest, AskResponse, SearchHit
from app.tools import build_tools
from app.tracing import tracer
from app.usage import record_usage


router = APIRouter(tags=["RAG"])

MAX_HISTORY_MESSAGES = 10
MIN_VECTOR_DISTANCE = 0.5

ASK_PROMPT_VERSION = "ask_v2"
ASK_PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "prompts"
    / f"{ASK_PROMPT_VERSION}.md"
)


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    if payload.conversation_id is not None:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.conversation_id == payload.conversation_id,
                Conversation.tenant_id == payload.tenant_id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            tenant_id=payload.tenant_id,
            title=payload.question.strip()[:120] or "New conversation",
        )
        db.add(conversation)
        db.flush()

    all_history = conversation.messages or []
    history = all_history[-MAX_HISTORY_MESSAGES:]

    with tracer.start_as_current_span("rag.retrieval") as retrieval_span:
        with tracer.start_as_current_span("retrieval.embed_query") as embed_span:
            embed_span.set_attribute("embedding.model", "nomic-embed-text")
            query_vector = embed(
                model="nomic-embed-text",
                input=payload.question,
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

        with tracer.start_as_current_span("retrieval.vector_search") as search_span:
            rows = db.execute(statement).all()
            search_span.set_attribute("retrieval.result_count", len(rows))

        sources = [
            SearchHit(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=float(1 - distance_value),
            )
            for chunk, distance_value in rows
        ]
        retrieval_span.set_attribute("retrieval.source_count", len(sources))

    if sources:
        excerpts = [
            {
                "document_id": source.document_id,
                "chunk_id": source.chunk_id,
                "text": source.content,
            }
            for source in sources
        ]

        messages = [
            {
                "role": "system",
                "content": ASK_PROMPT_PATH.read_text(encoding="utf-8"),
            },
            *history,
            {
                "role": "user",
                "content": (
                    f"Question: {payload.question}\n\n"
                    f"Document excerpts (JSON): {json.dumps(excerpts)}"
                ),
            },
        ]

        tool_functions = build_tools(db, payload.tenant_id)
        available_functions = {
            function.__name__: function
            for function in tool_functions
        }

        answer = None

        for _ in range(5):
            with tracer.start_as_current_span("llm.chat") as model_span:
                model_span.set_attribute("llm.model", "qwen2.5:1.5b")
                model_span.set_attribute("prompt.version", ASK_PROMPT_VERSION)
                response = chat(
                    model="qwen2.5:1.5b",
                    messages=messages,
                    tools=tool_functions,
                )

            record_usage(
                model="qwen2.5:1.5b",
                prompt_tokens=response.prompt_eval_count,
                completion_tokens=response.eval_count,
                prompt_version=ASK_PROMPT_VERSION,
            )

            messages.append(response.message)
            tool_calls = response.message.tool_calls or []

            if not tool_calls:
                answer = response.message.content or ""
                break

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                function = available_functions.get(tool_name)

                with tracer.start_as_current_span("tool.call") as tool_span:
                    tool_span.set_attribute("tool.name", tool_name)

                    if function is None:
                        result = {"error": f"Unknown tool: {tool_name}"}
                    else:
                        result = function(**tool_call.function.arguments)

                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": json.dumps(result),
                    }
                )
        else:
            raise HTTPException(
                status_code=502,
                detail="The model exceeded the tool-call limit",
            )

        available_pairs = {
            (source.document_id, source.chunk_id)
            for source in sources
        }

        def extract_citations(text: str) -> set[tuple[int, int]]:
            return {
                (int(document_id), int(chunk_id))
                for document_id, chunk_id in re.findall(
                    r"\[\s*document_id\s*=\s*(\d+)\s*,\s*chunk_id\s*=\s*(\d+)\s*\]",
                    text,
                )
            }

        citation_pairs = extract_citations(answer)

        if not citation_pairs or not citation_pairs.issubset(available_pairs):
            valid_citations = ", ".join(
                f"[document_id={document_id}, chunk_id={chunk_id}]"
                for document_id, chunk_id in sorted(available_pairs)
            )

            retry_messages = [
                *messages,
                {
                    "role": "user",
                    "content": (
                        "Rewrite your previous answer using the supplied excerpts. "
                        "Include at least one citation copied exactly from this list: "
                        f"{valid_citations}. Do not invent citation IDs."
                    ),
                },
            ]

            with tracer.start_as_current_span(
                "llm.chat.citation_retry"
            ) as model_span:
                model_span.set_attribute("llm.model", "qwen2.5:1.5b")
                model_span.set_attribute("prompt.version", ASK_PROMPT_VERSION)
                retry_response = chat(
                    model="qwen2.5:1.5b",
                    messages=retry_messages,
                )

            record_usage(
                model="qwen2.5:1.5b",
                prompt_tokens=retry_response.prompt_eval_count,
                completion_tokens=retry_response.eval_count,
                prompt_version=ASK_PROMPT_VERSION,
            )

            answer = retry_response.message.content or ""
            citation_pairs = extract_citations(answer)

        if not citation_pairs or not citation_pairs.issubset(available_pairs):
            raise HTTPException(
                status_code=502,
                detail="Model answer did not include valid chunk citations",
            )
    else:
        answer = "I couldn't find relevant information in this tenant's documents."

    conversation.messages = [
        *all_history,
        {"role": "user", "content": payload.question},
        {"role": "assistant", "content": answer},
    ]
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    return AskResponse(
        conversation_id=conversation.conversation_id,
        answer=answer,
        sources=sources,
    )