import tempfile
from typing import List
from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
from langchain_community.document_loaders import PDFPlumberLoader, WebBaseLoader, CSVLoader
from langchain_core.documents import Document
from app.models.document import Document as DBDocument
from app.services.embedder import get_embeddings

def process_documents_and_save(docs, db: Session):
    """
    Memecah dokumen (chunking), melakukan embedding, dan menyimpannya ke PostgreSQL
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = text_splitter.split_documents(docs)
    
    embeddings_model = get_embeddings()
    # Batch embed texts
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings_model.embed_documents(texts)
    
    for i, chunk in enumerate(chunks):
        doc_record = DBDocument(
            content=chunk.page_content,
            metadata_=chunk.metadata,
            embedding=vectors[i]
        )
        db.add(doc_record)
    
    db.commit()
    return len(chunks)

def ingest_pdf(file_content: bytes, filename: str, db: Session, prodi: str = None, bab: str = None):
    # Simpan file PDF ke temporary file untuk dibaca oleh PDFPlumberLoader
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    # Menggunakan PDFPlumberLoader alih-alih PyPDFLoader
    # PDFPlumber jauh lebih baik dalam membaca struktur tabel dan format kolom
    loader = PDFPlumberLoader(tmp_path)
    docs = loader.load()
    
    # Tambahkan filename dan metadata custom ke metadata agar ketahuan sumbernya
    for doc in docs:
        doc.metadata["source"] = filename
        if prodi:
            doc.metadata["prodi"] = prodi
        if bab:
            doc.metadata["bab"] = bab
            
    chunks_count = process_documents_and_save(docs, db)
    return chunks_count

def ingest_web(url: str, db: Session):
    loader = WebBaseLoader(url)
    docs = loader.load()
    
    chunks_count = process_documents_and_save(docs, db)
    return chunks_count

def ingest_csv(file_content: bytes, filename: str, db: Session, prodi: str = None, bab: str = None):
    # Simpan file CSV ke temporary file untuk dibaca oleh CSVLoader
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    # Menggunakan CSVLoader dari LangChain
    loader = CSVLoader(file_path=tmp_path, encoding='utf-8')
    docs = loader.load()
    
    # Tambahkan filename dan custom metadata ke metadata
    for doc in docs:
        doc.metadata["source"] = filename
        if prodi:
            doc.metadata["prodi"] = prodi
        if bab:
            doc.metadata["bab"] = bab
        
    chunks_count = process_documents_and_save(docs, db)
    return chunks_count

def ingest_json(file_content: bytes, filename: str, db: Session, prodi: str = None, bab: str = None):
    # Menggunakan Python json module langsung untuk menghindari masalah dependency 'jq' di Windows
    data = json.loads(file_content.decode('utf-8'))
    docs = []
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Konversi struktur dict menjadi teks (misal: "key: value")
                content_str = "\n".join([f"{k}: {v}" for k, v in item.items()])
                meta = {"source": filename}
                if prodi: meta["prodi"] = prodi
                if bab: meta["bab"] = bab
                doc = Document(page_content=content_str, metadata=meta)
                docs.append(doc)
    elif isinstance(data, dict):
        content_str = "\n".join([f"{k}: {v}" for k, v in data.items()])
        meta = {"source": filename}
        if prodi: meta["prodi"] = prodi
        if bab: meta["bab"] = bab
        doc = Document(page_content=content_str, metadata=meta)
        docs.append(doc)
    else:
        raise ValueError("Format JSON tidak valid. Harap gunakan array of object (List) atau object (Dict).")

    chunks_count = process_documents_and_save(docs, db)
    return chunks_count
