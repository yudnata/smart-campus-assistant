from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.chat_service import chat_rag
from app.services.ingest_service import ingest_pdf, ingest_web, ingest_csv, ingest_json
from app.models.document_chunk import DocumentChunk
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    topK: int = 5

class WebIngestRequest(BaseModel):
    url: str
    overwrite_old: bool = True

@router.post("/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        response = chat_rag(req.question, req.topK, db)
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
