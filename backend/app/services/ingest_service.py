import tempfile
from typing import List
from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
from langchain_community.document_loaders import PDFPlumberLoader, WebBaseLoader, CSVLoader
from langchain_core.documents import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedder import get_embeddings
import uuid

def process_documents_and_save(docs, db: Session, default_doc_type: str = "pedoman_akademik"):
    """
    Memecah dokumen (chunking), melakukan embedding, dan menyimpannya ke PostgreSQL
    dengan memetakan metadata ke kolom database yang terstruktur.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = text_splitter.split_documents(docs)
    
    if not chunks or all(not c.page_content.strip() for c in chunks):
        raise ValueError("Dokumen kosong atau tidak mengandung teks digital yang dapat dibaca. Jika berkas berupa hasil scan/gambar, silakan unggah dalam format Gambar (PNG/JPG/WEBP) agar diproses menggunakan OCR.")
    
    embeddings_model = get_embeddings()
    # Batch embed texts
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings_model.embed_documents(texts)
    
    for i, chunk in enumerate(chunks):
        metadata = chunk.metadata
        
        # Coba ambil halaman (LangChain PDFLoader biasanya menyimpannya di field 'page' 0-based)
        page_num = metadata.get("page")
        page_val = None
        if page_num is not None:
            page_val = page_num + 1  # ubah ke 1-based index
            
        page_start = metadata.get("page_start") or page_val
        page_end = metadata.get("page_end") or page_start
        
        pages_str = metadata.get("pages")
        if pages_str is None and page_start is not None:
            pages_str = str(page_start)
            if page_end is not None and page_end != page_start:
                pages_str = f"{page_start}-{page_end}"
        
        doc_record = DocumentChunk(
            id=uuid.uuid4().hex,
            content=chunk.page_content,
            source_file=metadata.get("source"),
            doc_type=metadata.get("doc_type") or default_doc_type,
            page_start=page_start,
            page_end=page_end,
            pages=pages_str,
            chapter=metadata.get("chapter"),
            section=metadata.get("section"),
            subsection=metadata.get("subsection"),
            section_path=metadata.get("section_path"),
            metadata_json=metadata,
            embedding=vectors[i]
        )
        db.add(doc_record)
    
    db.commit()
    return len(chunks)

def ingest_pdf(file_content: bytes, filename: str, db: Session, prodi: str = None, bab: str = None, overwrite_old: bool = True):
    if overwrite_old:
        db.query(DocumentChunk).filter(DocumentChunk.source_file == filename).delete()
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    loader = PDFPlumberLoader(tmp_path)
    docs = loader.load()
    
    # Periksa apakah ada teks digital yang terekstrak
    has_text = any(doc.page_content.strip() for doc in docs)
    
    if not has_text:
        # PDF Kosong / Hasil Scan - Jalankan OCR Fallback per Halaman
        try:
            import fitz
            from PIL import Image
            import pytesseract
            import os
            
            # Setup Tesseract path jika di Windows
            tesseract_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if os.path.exists(tesseract_win_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_win_path
                
            doc_fitz = fitz.open(stream=file_content, filetype="pdf")
            ocr_docs = []
            
            for i, page in enumerate(doc_fitz):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                try:
                    page_text = pytesseract.image_to_string(img, lang="ind+eng")
                except Exception:
                    page_text = pytesseract.image_to_string(img, lang="eng")
                
                cleaned_page_text = clean_text(page_text)
                if cleaned_page_text:
                    meta = {
                        "source": filename,
                        "doc_type": "pedoman_akademik_ocr",
                        "page": i  # 0-based index
                    }
                    if prodi:
                        meta["prodi"] = prodi
                    if bab:
                        meta["bab"] = bab
                    ocr_docs.append(Document(page_content=cleaned_page_text, metadata=meta))
            
            if ocr_docs:
                chunks_count = process_documents_and_save(ocr_docs, db, "pedoman_akademik_ocr")
                return chunks_count
        except Exception as ocr_err:
            # Jika OCR gagal, biarkan kode lanjut ke pelaporan error di bawah
            pass

    for doc in docs:
        doc.metadata["source"] = filename
        doc.metadata["doc_type"] = "pedoman_akademik"
        if prodi:
            doc.metadata["prodi"] = prodi
        if bab:
            doc.metadata["bab"] = bab
            
    chunks_count = process_documents_and_save(docs, db, "pedoman_akademik")
    return chunks_count

def ingest_web(url: str, db: Session, overwrite_old: bool = True):
    if overwrite_old:
        db.query(DocumentChunk).filter(DocumentChunk.source_file == url).delete()
        
    loader = WebBaseLoader(url)
    docs = loader.load()
    
    for doc in docs:
        doc.metadata["source"] = url
        doc.metadata["doc_type"] = "web_page"
        
    chunks_count = process_documents_and_save(docs, db, "web_page")
    return chunks_count

def ingest_csv(file_content: bytes, filename: str, db: Session, prodi: str = None, bab: str = None, overwrite_old: bool = True):
    if overwrite_old:
        db.query(DocumentChunk).filter(DocumentChunk.source_file == filename).delete()
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    loader = CSVLoader(file_path=tmp_path, encoding='utf-8')
    docs = loader.load()
    
    for doc in docs:
        doc.metadata["source"] = filename
        doc.metadata["doc_type"] = "csv_data"
        if prodi:
            doc.metadata["prodi"] = prodi
        if bab:
            doc.metadata["bab"] = bab
        
    chunks_count = process_documents_and_save(docs, db, "csv_data")
    return chunks_count

def ingest_json(file_content: bytes, filename: str, db: Session, prodi: str = None, bab: str = None, overwrite_old: bool = True):
    if overwrite_old:
        db.query(DocumentChunk).filter(DocumentChunk.source_file == filename).delete()
        
    data = json.loads(file_content.decode('utf-8'))
    docs = []
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                content_str = "\n".join([f"{k}: {v}" for k, v in item.items()])
                meta = {"source": filename, "doc_type": "json_data"}
                if prodi: meta["prodi"] = prodi
                if bab: meta["bab"] = bab
                doc = Document(page_content=content_str, metadata=meta)
                docs.append(doc)
    elif isinstance(data, dict):
        content_str = "\n".join([f"{k}: {v}" for k, v in data.items()])
        meta = {"source": filename, "doc_type": "json_data"}
        if prodi: meta["prodi"] = prodi
        if bab: meta["bab"] = bab
        doc = Document(page_content=content_str, metadata=meta)
        docs.append(doc)
    else:
        raise ValueError("Format JSON tidak valid. Harap gunakan array of object (List) atau object (Dict).")

    chunks_count = process_documents_and_save(docs, db, "json_data")
    return chunks_count


def clean_text(text: str) -> str:
    if not text:
        return ""
    import re
    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ingest_image(file_content: bytes, filename: str, db: Session, prodi: str = None, bab: str = None, overwrite_old: bool = True):
    if overwrite_old:
        db.query(DocumentChunk).filter(DocumentChunk.source_file == filename).delete()
        
    try:
        import pytesseract
        from PIL import Image
        import io
        import os
    except ImportError as e:
        raise ImportError(
            "Library OCR belum tersedia. Hubungi admin untuk menginstal pytesseract dan pillow."
        ) from e

    # Auto-detect Tesseract binary on Windows standard path
    tesseract_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_win_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_win_path

    try:
        image = Image.open(io.BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"File gambar rusak atau tidak didukung: {str(e)}")

    try:
        text = pytesseract.image_to_string(image, lang="ind+eng")
    except Exception:
        try:
            text = pytesseract.image_to_string(image, lang="eng")
        except Exception as e:
            raise RuntimeError(f"Gagal memproses OCR pada gambar: {str(e)}")

    cleaned_text = clean_text(text)
    if not cleaned_text or len(cleaned_text.strip()) < 5:
        raise ValueError("Gagal membaca teks dari gambar. Pastikan gambar memiliki resolusi yang cukup dan teks terbaca jelas.")

    # Simpan sebagai Document
    meta = {
        "source": filename,
        "doc_type": "calendar_image" if "kalender" in filename.lower() else "image_ocr",
    }
    if prodi:
        meta["prodi"] = prodi
    if bab:
        meta["bab"] = bab

    doc = Document(page_content=cleaned_text, metadata=meta)
    
    chunks_count = process_documents_and_save([doc], db, meta["doc_type"])
    return chunks_count
