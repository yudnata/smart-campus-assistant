import tempfile
from typing import List, Tuple, Dict, Any
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

def split_calendar_documents(docs: List[Document]) -> List[Document]:
    import re
    chunks = []
    
    # Month names in Indonesian and English
    months_pattern = r"(januari|februari|pebruari|maret|april|mei|juni|juli|agustus|september|oktober|november|nopember|desember|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    
    for doc in docs:
        filename = doc.metadata.get("source", "kalender")
        text = doc.page_content
        
        # Detect the academic year from the text or filename
        year_info = "Tahun Akademik 2026/2027"
        if "2025" in text or "2025" in filename:
            year_info = "Tahun Akademik 2025/2026"
        elif "2026" in text or "2026" in filename:
            year_info = "Tahun Akademik 2026/2027"
            
        lines = text.split("\n")
        
        current_semester = doc.metadata.get("semester", "")
        current_section = doc.metadata.get("section", "")
        
        current_activity_num = None
        current_activity_lines = []
        
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue
                
            # Detect Semester
            if "SEMESTER GASAL" in line_strip.upper():
                current_semester = "Semester Gasal"
                continue
            elif "SEMESTER GENAP" in line_strip.upper():
                current_semester = "Semester Genap"
                continue
                
            # Detect Section (starts with Roman numerals)
            section_match = re.match(r"^\s*([I|V|X]+)\.\s*(.*)", line_strip, re.IGNORECASE)
            if section_match:
                if current_activity_lines:
                    chunk_text = " ".join(current_activity_lines)
                    # Construct content
                    context_parts = ["Kalender Akademik Universitas Udayana", year_info]
                    if current_semester: context_parts.append(current_semester)
                    if current_section: context_parts.append(current_section)
                    context_str = " | ".join(context_parts)
                    full_content = f"{context_str}\nKegiatan: {chunk_text}"
                    
                    meta = doc.metadata.copy()
                    meta.update({
                        "doc_type": "calendar_chunk",
                        "semester": current_semester,
                        "section": current_section
                    })
                    chunks.append(Document(page_content=full_content, metadata=meta))
                    
                    current_activity_lines = []
                    current_activity_num = None
                    
                current_section = f"{section_match.group(1)}. {section_match.group(2)}"
                continue
                
            # Detect if a line starts with a number (excluding years)
            num_match = re.match(r"^\s*(\d{1,2})\b\.?\s*[|]?\s*(.*)", line_strip)
            if num_match:
                num_val = int(num_match.group(1))
                if num_val < 100: 
                    if current_activity_lines:
                        chunk_text = " ".join(current_activity_lines)
                        # Construct content
                        context_parts = ["Kalender Akademik Universitas Udayana", year_info]
                        if current_semester: context_parts.append(current_semester)
                        if current_section: context_parts.append(current_section)
                        context_str = " | ".join(context_parts)
                        full_content = f"{context_str}\nKegiatan: {chunk_text}"
                        
                        meta = doc.metadata.copy()
                        meta.update({
                            "doc_type": "calendar_chunk",
                            "semester": current_semester,
                            "section": current_section
                        })
                        chunks.append(Document(page_content=full_content, metadata=meta))
                        
                    current_activity_num = num_val
                    current_activity_lines = [line_strip]
                    continue
                    
            if current_activity_num is not None:
                current_activity_lines.append(line_strip)
            else:
                if re.search(months_pattern, line_strip, re.IGNORECASE):
                    if current_activity_lines:
                        chunk_text = " ".join(current_activity_lines)
                        # Construct content
                        context_parts = ["Kalender Akademik Universitas Udayana", year_info]
                        if current_semester: context_parts.append(current_semester)
                        if current_section: context_parts.append(current_section)
                        context_str = " | ".join(context_parts)
                        full_content = f"{context_str}\nKegiatan: {chunk_text}"
                        
                        meta = doc.metadata.copy()
                        meta.update({
                            "doc_type": "calendar_chunk",
                            "semester": current_semester,
                            "section": current_section
                        })
                        chunks.append(Document(page_content=full_content, metadata=meta))
                        current_activity_lines = []
                        
                    # Also append this standalone line
                    context_parts = ["Kalender Akademik Universitas Udayana", year_info]
                    if current_semester: context_parts.append(current_semester)
                    if current_section: context_parts.append(current_section)
                    context_str = " | ".join(context_parts)
                    full_content = f"{context_str}\nKegiatan: {line_strip}"
                    
                    meta = doc.metadata.copy()
                    meta.update({
                        "doc_type": "calendar_chunk",
                        "semester": current_semester,
                        "section": current_section
                    })
                    chunks.append(Document(page_content=full_content, metadata=meta))
                    
        # Append the last item in doc
        if current_activity_lines:
            chunk_text = " ".join(current_activity_lines)
            context_parts = ["Kalender Akademik Universitas Udayana", year_info]
            if current_semester: context_parts.append(current_semester)
            if current_section: context_parts.append(current_section)
            context_str = " | ".join(context_parts)
            full_content = f"{context_str}\nKegiatan: {chunk_text}"
            
            meta = doc.metadata.copy()
            meta.update({
                "doc_type": "calendar_chunk",
                "semester": current_semester,
                "section": current_section
            })
            chunks.append(Document(page_content=full_content, metadata=meta))
            
    return chunks


def parse_and_split_file(
    file_content: bytes,
    filename: str,
    prodi: str = None,
    bab: str = None,
    semester: str = None,
    tahun_akademik: str = None
) -> Tuple[List[Document], str]:
    import os
    ext = os.path.splitext(filename)[1].lower()
    
    docs = []
    default_doc_type = "pedoman_akademik"
    
    if ext == ".pdf":
        from app.services.pipeline_parser import parse_pdf_to_pipeline_chunks
        pipeline_chunks, doc_type = parse_pdf_to_pipeline_chunks(file_content, filename)
        
        docs = []
        for chunk in pipeline_chunks:
            meta = chunk.metadata.copy()
            meta["source"] = filename
            if prodi:
                meta["prodi"] = prodi
            if bab:
                meta["bab"] = bab
            if semester:
                meta["semester"] = semester
            if tahun_akademik:
                meta["tahun_akademik"] = tahun_akademik
            docs.append(Document(page_content=chunk.text, metadata=meta))
            
        return docs, doc_type
                    
    elif ext == ".csv":
        import tempfile
        from langchain_community.document_loaders import CSVLoader
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        try:
            loader = CSVLoader(file_path=tmp_path, encoding='utf-8')
            docs = loader.load()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        
        default_doc_type = "csv_data"
        for doc in docs:
            doc.metadata["source"] = filename
            doc.metadata["doc_type"] = "csv_data"
            if prodi:
                doc.metadata["prodi"] = prodi
            if bab:
                doc.metadata["bab"] = bab
            if semester:
                doc.metadata["semester"] = semester
            if tahun_akademik:
                doc.metadata["tahun_akademik"] = tahun_akademik
                
    elif ext == ".json":
        import json
        data = json.loads(file_content.decode('utf-8'))
        default_doc_type = "json_data"
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    content_str = "\n".join([f"{k}: {v}" for k, v in item.items()])
                    meta = {"source": filename, "doc_type": "json_data"}
                    if prodi: meta["prodi"] = prodi
                    if bab: meta["bab"] = bab
                    if semester: meta["semester"] = semester
                    if tahun_akademik: meta["tahun_akademik"] = tahun_akademik
                    docs.append(Document(page_content=content_str, metadata=meta))
        elif isinstance(data, dict):
            content_str = "\n".join([f"{k}: {v}" for k, v in data.items()])
            meta = {"source": filename, "doc_type": "json_data"}
            if prodi: meta["prodi"] = prodi
            if bab: meta["bab"] = bab
            if semester: meta["semester"] = semester
            if tahun_akademik: meta["tahun_akademik"] = tahun_akademik
            docs.append(Document(page_content=content_str, metadata=meta))
        else:
            raise ValueError("Format JSON tidak valid. Harap gunakan array of object (List) atau object (Dict).")
            
    elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            import pytesseract
            from PIL import Image
            import io
            import os
        except ImportError as e:
            raise ImportError(
                "Library OCR belum tersedia. Hubungi admin untuk menginstal pytesseract dan pillow."
            ) from e
            
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
            
        default_doc_type = "calendar_image" if "kalender" in filename.lower() else "image_ocr"
        meta = {
            "source": filename,
            "doc_type": default_doc_type,
        }
        if prodi:
            meta["prodi"] = prodi
        if bab:
            meta["bab"] = bab
        if semester:
            meta["semester"] = semester
        if tahun_akademik:
            meta["tahun_akademik"] = tahun_akademik
        docs = [Document(page_content=cleaned_text, metadata=meta)]
    else:
        raise ValueError("Format file tidak didukung.")
        
    # Deteksi apakah berkas merupakan kalender akademik
    is_calendar = False
    filename_lower = filename.lower()
    if "kalender" in filename_lower or "calendar" in filename_lower or "kegiatan" in filename_lower:
        is_calendar = True
    else:
        for doc in docs:
            if "KALENDER AKADEMIK" in doc.page_content.upper():
                is_calendar = True
                break
                
    if is_calendar:
        chunks = split_calendar_documents(docs)
        if chunks:
            # Overwrite doc_type if we parsed calendar chunks
            for c in chunks:
                if semester:
                    c.metadata["semester"] = semester
                if tahun_akademik:
                    c.metadata["tahun_akademik"] = tahun_akademik
            default_doc_type = "calendar_chunk"
    else:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_documents(docs)
        for c in chunks:
            if semester:
                c.metadata["semester"] = semester
            if tahun_akademik:
                c.metadata["tahun_akademik"] = tahun_akademik
        
    if not chunks or all(not c.page_content.strip() for c in chunks):
        raise ValueError("Dokumen kosong atau tidak mengandung teks digital yang dapat dibaca. Jika berkas berupa hasil scan/gambar, silakan unggah dalam format Gambar (PNG/JPG/WEBP) agar diproses menggunakan OCR.")
        
    return chunks, default_doc_type


def save_chunks_to_db(chunks_data: List[Dict[str, Any]], default_doc_type: str, overwrite_old: bool, db: Session) -> int:
    if not chunks_data:
        return 0
        
    # Ambil source_file dari metadata chunk pertama
    first_metadata = chunks_data[0].get("metadata", {})
    source_file = first_metadata.get("source")
    
    if overwrite_old and source_file:
        db.query(DocumentChunk).filter(DocumentChunk.source_file == source_file).delete()
        
    embeddings_model = get_embeddings()
    texts = [c["page_content"] for c in chunks_data]
    vectors = embeddings_model.embed_documents(texts)
    
    for i, c in enumerate(chunks_data):
        metadata = c.get("metadata", {})
        
        page_num = metadata.get("page")
        page_val = None
        if page_num is not None:
            page_val = page_num + 1
            
        page_start = metadata.get("page_start") or page_val
        page_end = metadata.get("page_end") or page_start
        
        pages_str = metadata.get("pages")
        if pages_str is None and page_start is not None:
            pages_str = str(page_start)
            if page_end is not None and page_end != page_start:
                pages_str = f"{page_start}-{page_end}"
                
        doc_record = DocumentChunk(
            id=uuid.uuid4().hex,
            content=c["page_content"],
            source_file=metadata.get("source") or source_file,
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
    return len(chunks_data)


def ingest_pdf(
    file_content: bytes,
    filename: str,
    db: Session,
    prodi: str = None,
    bab: str = None,
    semester: str = None,
    tahun_akademik: str = None,
    overwrite_old: bool = True
):
    chunks, doc_type = parse_and_split_file(file_content, filename, prodi, bab, semester, tahun_akademik)
    chunks_data = [{"page_content": chunk.page_content, "metadata": chunk.metadata} for chunk in chunks]
    return save_chunks_to_db(chunks_data, doc_type, overwrite_old, db)


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


def ingest_csv(
    file_content: bytes,
    filename: str,
    db: Session,
    prodi: str = None,
    bab: str = None,
    semester: str = None,
    tahun_akademik: str = None,
    overwrite_old: bool = True
):
    chunks, doc_type = parse_and_split_file(file_content, filename, prodi, bab, semester, tahun_akademik)
    chunks_data = [{"page_content": chunk.page_content, "metadata": chunk.metadata} for chunk in chunks]
    return save_chunks_to_db(chunks_data, doc_type, overwrite_old, db)


def ingest_json(
    file_content: bytes,
    filename: str,
    db: Session,
    prodi: str = None,
    bab: str = None,
    semester: str = None,
    tahun_akademik: str = None,
    overwrite_old: bool = True
):
    chunks, doc_type = parse_and_split_file(file_content, filename, prodi, bab, semester, tahun_akademik)
    chunks_data = [{"page_content": chunk.page_content, "metadata": chunk.metadata} for chunk in chunks]
    return save_chunks_to_db(chunks_data, doc_type, overwrite_old, db)


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


def ingest_image(
    file_content: bytes,
    filename: str,
    db: Session,
    prodi: str = None,
    bab: str = None,
    semester: str = None,
    tahun_akademik: str = None,
    overwrite_old: bool = True
):
    chunks, doc_type = parse_and_split_file(file_content, filename, prodi, bab, semester, tahun_akademik)
    chunks_data = [{"page_content": chunk.page_content, "metadata": chunk.metadata} for chunk in chunks]
    return save_chunks_to_db(chunks_data, doc_type, overwrite_old, db)
