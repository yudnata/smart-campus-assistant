import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.endpoints import router
from sqlalchemy import text

from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

# Setup DB Tables (Ini akan membuat tabel documents jika belum ada)
# Note: Ekstensi pgvector HARUS sudah diaktifkan di PostgreSQL database (`CREATE EXTENSION vector;`)
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
except Exception as e:
    print(f"Warning: Could not create vector extension automatically: {e}")

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.project_name, version=settings.version)

# Setup CORS agar React/Flutter bisa akses
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Ganti dengan domain production Anda nanti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import router as auth_router
from app.api.chat_history import router as chat_history_router

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_history_router, prefix="/api/chat/conversations", tags=["chat_history"])

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "STKI RAG Backend is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
