from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Conversation
from app.schemas import ConversationOut, ConversationRename, ConversationSummary


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    tenant_id: int = Query(gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.tenant_id == tenant_id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [
        ConversationSummary(
            conversation_id=item.conversation_id,
            title=item.title,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    tenant_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationOut(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        messages=conversation.messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )

@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: int,
    payload: ConversationRename,
    tenant_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.title = payload.title.strip()
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ConversationOut(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        messages=conversation.messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )

@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    tenant_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()