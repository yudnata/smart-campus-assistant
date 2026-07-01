from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from typing import List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.schemas.rag import ChatRequest, ChatResponse
from app.services.chat_service import chat_rag
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter()

def get_current_admin(current_user: User = Depends(get_current_user)):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang diperbolehkan mengakses fitur ini."
        )
    return current_user

from app.models.message import Message

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
    semester: str = Form(None),
    tahun_akademik: str = Form(None),
    overwrite_old: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from app.services.ingest_service import ingest_csv, ingest_json, ingest_pdf, ingest_image
    import os

    content = await file.read()
    ext = os.path.splitext(file.filename)[1].lower()

    if ext == ".pdf":
        try:
            chunks_added = ingest_pdf(content, file.filename, db, prodi, bab, semester, tahun_akademik, overwrite_old)
            return {"message": "Berhasil memproses PDF", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses PDF: {str(e)}") from e

    if ext == ".csv":
        try:
            chunks_added = ingest_csv(content, file.filename, db, prodi, bab, semester, tahun_akademik, overwrite_old)
            return {"message": "Berhasil memproses CSV", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses CSV: {str(e)}") from e

    if ext == ".json":
        try:
            chunks_added = ingest_json(content, file.filename, db, prodi, bab, semester, tahun_akademik, overwrite_old)
            return {"message": "Berhasil memproses JSON", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses JSON: {str(e)}") from e

    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            chunks_added = ingest_image(content, file.filename, db, prodi, bab, semester, tahun_akademik, overwrite_old)
            return {"message": "Berhasil memproses Gambar (OCR)", "chunks_added": chunks_added}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal memproses Gambar (OCR): {str(e)}") from e

    raise HTTPException(status_code=400, detail="Hanya file PDF, CSV, JSON, dan Gambar (PNG/JPG/JPEG/WEBP) yang didukung")


class ConfirmSaveChunk(BaseModel):
    page_content: str
    metadata: Dict[str, Any]


class ConfirmSaveRequest(BaseModel):
    chunks: List[ConfirmSaveChunk]
    doc_type: str
    overwrite_old: bool = True


@router.post("/ingest/preview-file")
async def ingest_preview_file_endpoint(
    file: UploadFile = File(...),
    prodi: str = Form(None),
    bab: str = Form(None),
    semester: str = Form(None),
    tahun_akademik: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from app.services.ingest_service import parse_and_split_file
    
    try:
        content = await file.read()
        chunks, doc_type = parse_and_split_file(content, file.filename, prodi, bab, semester, tahun_akademik)
        return {
            "filename": file.filename,
            "doc_type": doc_type,
            "chunks": [
                {
                    "page_content": chunk.page_content,
                    "metadata": chunk.metadata
                }
                for chunk in chunks
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mempratinjau file: {str(e)}") from e


@router.post("/ingest/confirm-save")
def ingest_confirm_save_endpoint(
    req: ConfirmSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from app.services.ingest_service import save_chunks_to_db
    
    try:
        chunks_data = [
            {"page_content": chunk.page_content, "metadata": chunk.metadata}
            for chunk in req.chunks
        ]
        chunks_added = save_chunks_to_db(chunks_data, req.doc_type, req.overwrite_old, db)
        return {"message": "Berhasil menyimpan dokumen ke database RAG", "chunks_added": chunks_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan dokumen: {str(e)}") from e


@router.post("/ingest/url")
def ingest_url_endpoint(
    req: WebIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from app.services.ingest_service import ingest_web

    try:
        chunks_added = ingest_web(req.url, db, req.overwrite_old)
        return {"message": "Berhasil", "chunks_added": chunks_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ingest/documents")
def get_ingested_documents(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    from sqlalchemy import func
    results = db.query(
        DocumentChunk.source_file,
        DocumentChunk.doc_type,
        func.count(DocumentChunk.id).label("total_chunks"),
        func.min(DocumentChunk.created_at).label("first_created")
    ).group_by(
        DocumentChunk.source_file,
        DocumentChunk.doc_type
    ).order_by(
        func.min(DocumentChunk.created_at).desc()
    ).all()
    
    return [
        {
            "source_file": r.source_file or "Unknown Source",
            "doc_type": r.doc_type or "Unknown Type",
            "total_chunks": r.total_chunks,
            "created_at": r.first_created.isoformat() if r.first_created else None
        }
        for r in results
    ]


@router.delete("/ingest/documents")
def delete_ingested_document(
    source_file: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    deleted_count = db.query(DocumentChunk).filter(DocumentChunk.source_file == source_file).delete()
    db.commit()
    return {"message": f"Berhasil menghapus dokumen {source_file}", "chunks_deleted": deleted_count}


@router.get("/stats")
def stats_endpoint(db: Session = Depends(get_db)):
    total = db.query(DocumentChunk).count()
    return {"totalChunks": total}

