import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.endpoints import router
from app.core.config import settings
from app.core.database import Base, engine

from app.models.conversation import Conversation
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.models.user import User


def prepare_database() -> None:
    """
    Menyiapkan ekstensi, tabel, dan index database bila koneksi tersedia.
    Jika NeonDB belum bisa dijangkau saat startup, aplikasi tetap hidup dan
    endpoint yang memakai database akan mengembalikan error yang jelas.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not create vector extension automatically: {e}")

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create database tables automatically: {e}")
        return

    # Auto-migration: Ensure is_admin column exists in users table
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;"))
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not add is_admin column automatically: {e}")

    # Auto-creation: Ensure admin@gmail.com exists with password admin123
    try:
        from sqlalchemy.orm import Session
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.core.security import get_password_hash

        db: Session = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.email == "admin@gmail.com").first()
            if not admin_user:
                hashed_pw = get_password_hash("admin123")
                new_admin = User(
                    email="admin@gmail.com",
                    name="Administrator",
                    hashed_password=hashed_pw,
                    is_verified=True,
                    is_admin=True
                )
                db.add(new_admin)
                db.commit()
                print("Admin user created successfully (admin@gmail.com / admin123)")
            else:
                # Ensure existing admin has is_admin and is_verified set to True
                if not admin_user.is_admin or not admin_user.is_verified:
                    admin_user.is_admin = True
                    admin_user.is_verified = True
                    db.commit()
                    print("Admin user permissions updated successfully")
        finally:
            db.close()
    except Exception as e:
        print(f"Warning: Could not auto-create admin user: {e}")

    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx
                    ON public.document_chunks
                    USING hnsw (embedding vector_cosine_ops);
                    """
                )
            )
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not create HNSW index automatically: {e}")


prepare_database()

app = FastAPI(title=settings.project_name, version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
