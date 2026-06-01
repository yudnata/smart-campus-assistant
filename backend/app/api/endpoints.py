from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.chat_service import chat_rag
from app.services.ingest_service import ingest_pdf, ingest_web
from app.models.document import Document
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    topK: int = 5

class WebIngestRequest(BaseModel):
    url: str

@router.post("/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        response = chat_rag(req.question, req.topK, db)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/file")
async def ingest_file_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung")
    
    content = await file.read()
    try:
        chunks_added = ingest_pdf(content, file.filename, db)
        return {"message": "Berhasil", "chunks_added": chunks_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/url")
def ingest_url_endpoint(req: WebIngestRequest, db: Session = Depends(get_db)):
    try:
        chunks_added = ingest_web(req.url, db)
        return {"message": "Berhasil", "chunks_added": chunks_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def stats_endpoint(db: Session = Depends(get_db)):
    total = db.query(Document).count()
    return {"totalChunks": total}
