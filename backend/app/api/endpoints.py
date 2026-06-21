from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.chat_service import chat_rag
from app.services.ingest_service import ingest_pdf, ingest_web, ingest_csv, ingest_json
from app.models.document_chunk import DocumentChunk
from pydantic import BaseModel

router = APIRouter()

from app.models.message import Message

class ChatRequest(BaseModel):
    question: str
    topK: int = 5
    conversation_id: str = None # Optional for guest

class WebIngestRequest(BaseModel):
    url: str
    overwrite_old: bool = True

@router.post("/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        # Jika conversation_id ada, simpan pesan user terlebih dahulu
        if req.conversation_id:
            user_msg = Message(
                conversation_id=req.conversation_id,
                role="user",
                content=req.question
            )
            db.add(user_msg)
            db.commit()

        # Generate response using RAG
        response = chat_rag(req.question, req.topK, db)
        
        # Simpan balasan bot jika conversation_id valid
        if req.conversation_id:
            bot_msg = Message(
                conversation_id=req.conversation_id,
                role="assistant",
                content=response.get("answer", "Maaf, terjadi kesalahan.")
            )
            db.add(bot_msg)
            db.commit()
            
            # Update the conversation updated_at
            from app.models.conversation import Conversation
            from sqlalchemy.sql import func
            conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
            if conv:
                conv.updated_at = func.now()
                db.commit()

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/file")
async def ingest_file_endpoint(
    file: UploadFile = File(...), 
    prodi: str = Form(None),
    bab: str = Form(None),
    overwrite_old: bool = Form(True),
    db: Session = Depends(get_db)
):
    content = await file.read()
    
    if file.filename.endswith(".pdf"):
        try:
            chunks_added = ingest_pdf(content, file.filename, db, prodi, bab, overwrite_old)
            return {"message": "Berhasil memproses PDF", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses PDF: {str(e)}")
            
    elif file.filename.endswith(".csv"):
        try:
            chunks_added = ingest_csv(content, file.filename, db, prodi, bab, overwrite_old)
            return {"message": "Berhasil memproses CSV", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses CSV: {str(e)}")
            
    elif file.filename.endswith(".json"):
        try:
            chunks_added = ingest_json(content, file.filename, db, prodi, bab, overwrite_old)
            return {"message": "Berhasil memproses JSON", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses JSON: {str(e)}")
            
    else:
        raise HTTPException(status_code=400, detail="Hanya file PDF, CSV, dan JSON yang didukung")

@router.post("/ingest/url")
def ingest_url_endpoint(req: WebIngestRequest, db: Session = Depends(get_db)):
    try:
        chunks_added = ingest_web(req.url, db, req.overwrite_old)
        return {"message": "Berhasil", "chunks_added": chunks_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def stats_endpoint(db: Session = Depends(get_db)):
    total = db.query(DocumentChunk).count()
    return {"totalChunks": total}
