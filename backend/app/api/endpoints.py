from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.schemas.rag import ChatRequest, ChatResponse
from app.services.chat_service import chat_rag

router = APIRouter()

from app.models.message import Message

class ChatRequest(BaseModel):
    question: str
    topK: int = 10
    conversation_id: str = None # Optional for guest

class WebIngestRequest(BaseModel):
    url: str
    overwrite_old: bool = True


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        if req.conversation_id:
            user_msg = Message(
                conversation_id=req.conversation_id,
                role="user",
                content=req.question,
            )
            db.add(user_msg)
            db.commit()

        response = chat_rag(req.question, req.top_k, db)

        if req.conversation_id:
            bot_msg = Message(
                conversation_id=req.conversation_id,
                role="assistant",
                content=response.get("answer", "Maaf, terjadi kesalahan."),
            )
            db.add(bot_msg)
            db.commit()

            from app.models.conversation import Conversation
            from sqlalchemy.sql import func

            conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
            if conv:
                conv.updated_at = func.now()
                db.commit()

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ingest/file")
async def ingest_file_endpoint(
    file: UploadFile = File(...),
    prodi: str = Form(None),
    bab: str = Form(None),
    overwrite_old: bool = Form(True),
    db: Session = Depends(get_db),
):
    from app.services.ingest_service import ingest_csv, ingest_json, ingest_pdf

    content = await file.read()

    if file.filename.endswith(".pdf"):
        try:
            chunks_added = ingest_pdf(content, file.filename, db, prodi, bab, overwrite_old)
            return {"message": "Berhasil memproses PDF", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses PDF: {str(e)}") from e

    if file.filename.endswith(".csv"):
        try:
            chunks_added = ingest_csv(content, file.filename, db, prodi, bab, overwrite_old)
            return {"message": "Berhasil memproses CSV", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses CSV: {str(e)}") from e

    if file.filename.endswith(".json"):
        try:
            chunks_added = ingest_json(content, file.filename, db, prodi, bab, overwrite_old)
            return {"message": "Berhasil memproses JSON", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses JSON: {str(e)}") from e

    raise HTTPException(status_code=400, detail="Hanya file PDF, CSV, dan JSON yang didukung")


@router.post("/ingest/url")
def ingest_url_endpoint(req: WebIngestRequest, db: Session = Depends(get_db)):
    from app.services.ingest_service import ingest_web

    try:
        chunks_added = ingest_web(req.url, db, req.overwrite_old)
        return {"message": "Berhasil", "chunks_added": chunks_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats")
def stats_endpoint(db: Session = Depends(get_db)):
    total = db.query(DocumentChunk).count()
    return {"totalChunks": total}

