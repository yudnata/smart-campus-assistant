from pathlib import Path
import json

from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.models.document_chunk import DocumentChunk


# ============================================================
# KONFIGURASI
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

CHUNKS_PATH = (
    PROJECT_ROOT
    / "data_extraction"
    / "data"
    / "processed"
    / "chunks"
    / "chunks.json"
)

MODEL_NAME = "intfloat/multilingual-e5-large"
BATCH_SIZE = 8


# ============================================================
# UTILITAS
# ============================================================

def load_chunks(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"File chunks.json tidak ditemukan: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_embedding_text(chunk: dict) -> str:
    """
    Teks yang di-embedding dibuat lebih kaya konteks.
    Tidak hanya isi chunk, tetapi juga metadata penting.
    """
    metadata = chunk.get("metadata", {})

    parts = [
        f"Jenis Dokumen: {metadata.get('doc_type', '')}",
        f"Sumber: {metadata.get('source_file', '')}",
        f"Bagian: {metadata.get('section_path', '')}",
        "",
        chunk.get("text", ""),
    ]

    return "\n".join(part for part in parts if part.strip())


def upsert_chunks(
    db: Session,
    chunks: list[dict],
    embeddings,
) -> None:
    for chunk, embedding in zip(chunks, embeddings):
        metadata = chunk.get("metadata", {})

        existing = db.get(DocumentChunk, chunk["id"])

        if existing:
            existing.content = chunk["text"]
            existing.source_file = metadata.get("source_file")
            existing.doc_type = metadata.get("doc_type")
            existing.page_start = metadata.get("page_start")
            existing.page_end = metadata.get("page_end")
            existing.pages = metadata.get("pages")
            existing.chapter = metadata.get("chapter")
            existing.section = metadata.get("section")
            existing.subsection = metadata.get("subsection")
            existing.section_path = metadata.get("section_path")
            existing.metadata_json = metadata
            existing.embedding = embedding.tolist()
        else:
            db.add(
                DocumentChunk(
                    id=chunk["id"],
                    content=chunk["text"],
                    source_file=metadata.get("source_file"),
                    doc_type=metadata.get("doc_type"),
                    page_start=metadata.get("page_start"),
                    page_end=metadata.get("page_end"),
                    pages=metadata.get("pages"),
                    chapter=metadata.get("chapter"),
                    section=metadata.get("section"),
                    subsection=metadata.get("subsection"),
                    section_path=metadata.get("section_path"),
                    metadata_json=metadata,
                    embedding=embedding.tolist(),
                )
            )

    db.commit()


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("[INFO] Membuat tabel jika belum ada...")
    Base.metadata.create_all(bind=engine)

    print(f"[INFO] Membaca chunks dari: {CHUNKS_PATH}")
    chunks = load_chunks(CHUNKS_PATH)
    print(f"[INFO] Total chunk: {len(chunks)}")

    print(f"[INFO] Memuat embedding model: {MODEL_NAME} pada GPU")
    model = SentenceTransformer(MODEL_NAME, device="cuda")

    texts_for_embedding = [build_embedding_text(chunk) for chunk in chunks]

    print("[INFO] Membuat embedding...")
    embeddings = model.encode(
        texts_for_embedding,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    db = SessionLocal()

    try:
        print("[INFO] Memasukkan chunk + embedding ke PostgreSQL...")
        for start in tqdm(range(0, len(chunks), BATCH_SIZE)):
            end = start + BATCH_SIZE
            upsert_chunks(
                db=db,
                chunks=chunks[start:end],
                embeddings=embeddings[start:end],
            )

    finally:
        db.close()

    print("[SELESAI] Ingest chunks ke PostgreSQL selesai.")


if __name__ == "__main__":
    main()