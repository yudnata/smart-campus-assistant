import tempfile
from typing import List
from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from app.models.document import Document
from app.services.embedder import get_embeddings

def process_documents_and_save(docs, db: Session):
    """
    Memecah dokumen (chunking), melakukan embedding, dan menyimpannya ke PostgreSQL
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = text_splitter.split_documents(docs)
    
    embeddings_model = get_embeddings()
    # Batch embed texts
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings_model.embed_documents(texts)
    
    for i, chunk in enumerate(chunks):
        doc_record = Document(
            content=chunk.page_content,
            metadata_=chunk.metadata,
            embedding=vectors[i]
        )
        db.add(doc_record)
    
    db.commit()
    return len(chunks)

def ingest_pdf(file_content: bytes, filename: str, db: Session):
    # Simpan file PDF ke temporary file untuk dibaca oleh PyPDFLoader
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    
    # Tambahkan filename ke metadata agar ketahuan sumbernya
    for doc in docs:
        doc.metadata["source"] = filename
        
    chunks_count = process_documents_and_save(docs, db)
    return chunks_count

def ingest_web(url: str, db: Session):
    loader = WebBaseLoader(url)
    docs = loader.load()
    
    chunks_count = process_documents_and_save(docs, db)
    return chunks_count
