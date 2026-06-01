import time
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document import Document
from app.services.embedder import get_embeddings
from app.services.llm_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
import logging

logging.basicConfig(level=logging.INFO)

PROMPT_TEMPLATE = """
Anda adalah asisten virtual resmi untuk layanan Akademik Kampus. 
Gunakan HANYA informasi dari dokumen pedoman akademik berikut untuk menjawab pertanyaan pengguna.
Jika informasi tidak ada di dalam dokumen, katakan "Maaf, informasi tersebut tidak ditemukan dalam pedoman akademik."
Jangan mengarang (halusinasi) informasi tambahan.
Gunakan bahasa yang ramah, profesional, dan mudah dipahami.

---
KONTEKS DOKUMEN:
{context}

---
PERTANYAAN PENGGUNA:
{question}
"""

def chat_rag(question: str, top_k: int, db: Session):
    start_time = time.time()
    
    # 1. Ubah pertanyaan menjadi vektor
    embeddings_model = get_embeddings()
    query_vector = embeddings_model.embed_query(question)
    
    # 2. Cari ke PostgreSQL (pgvector) dengan Cosine Distance (<=>)
    # Cosine distance = 1 - Cosine Similarity
    # Kita menggunakan ORDER BY embedding <=> query_vector
    
    query = f"""
        SELECT id, content, metadata, 1 - (embedding <=> :vector) AS similarity
        FROM documents
        ORDER BY embedding <=> :vector
        LIMIT :top_k
    """
    
    # Format vektor ke string agar PostgreSQL memahaminya
    vector_str = str(query_vector)
    
    results = db.execute(
        text(query),
        {"vector": vector_str, "top_k": top_k}
    ).fetchall()
    
    chunks_found = len(results)
    
    if chunks_found == 0:
        return {
            "answer": "Belum ada pedoman akademik yang diunggah ke dalam sistem.",
            "sources": [],
            "stats": None
        }
    
    # 3. Siapkan konteks untuk LLM
    context_text = "\n\n".join([f"Sumber: {row.metadata.get('source', 'Unknown')} - Teks: {row.content}" for row in results])
    
    top_similarity = results[0].similarity if chunks_found > 0 else 0.0
    
    # 4. Generate jawaban dengan LLM
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    llm = get_llm()
    
    chain = prompt | llm
    response = chain.invoke({"context": context_text, "question": question})
    
    # 5. Susun Response Data
    retrieval_time_ms = int((time.time() - start_time) * 1000)
    
    sources = []
    for row in results:
        sources.append({
            "page": row.metadata.get("page", 1),
            "preview": row.content[:150] + "...",
            "similarity": float(row.similarity),
            "source": row.metadata.get("source", "Unknown")
        })
        
    stats = {
        "retrievalTimeMs": retrieval_time_ms,
        "chunksFound": chunks_found,
        "topSimilarity": float(top_similarity)
    }
    
    return {
        "answer": response.content,
        "sources": sources,
        "stats": stats
    }
