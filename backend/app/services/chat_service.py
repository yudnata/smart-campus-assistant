import logging
import re
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embedder import get_embeddings
from app.services.groq_service import generate_answer

logging.basicConfig(level=logging.INFO)

NO_CONTEXT_ANSWER = "Informasi tersebut tidak ditemukan di dokumen yang tersedia."


def _format_pgvector(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


# ============================================================
# YEAR-AWARE + KEYWORD RE-RANKING
# ============================================================

# Stopword Indonesia umum yang tidak memberi info topik
_STOPWORDS_ID = {
    "kapan", "apa", "siapa", "dimana", "kenapa", "bagaimana", "apakah",
    "yang", "dan", "atau", "di", "ke", "dari", "pada", "untuk", "dengan",
    "adalah", "ini", "itu", "akan", "sudah", "ada", "tidak", "bisa",
    "dalam", "tentang", "saat", "waktu", "saya", "kamu", "kita", "mereka",
    "jadwal", "kegiatan", "tanggal", "tahun", "semester",
}


def _extract_years_from_query(question: str) -> list[int]:
    """Ekstrak tahun 4-digit (2020–2030) yang disebutkan dalam pertanyaan."""
    years = re.findall(r'\b(202[0-9])\b', question)
    return list({int(y) for y in years})


def _extract_query_keywords(question: str) -> list[str]:
    """Ekstrak kata kunci penting dari query (buang stopword, min 3 karakter)."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
    return [w for w in words if w not in _STOPWORDS_ID]


def _compute_year_boost(item: dict, target_years: list[int]) -> float:
    """
    Hitung faktor penguat skor berdasarkan relevansi tahun.
    Hanya memeriksa ISI KONTEN chunk (bukan nama file) karena nama file
    bisa ambigu — misalnya "2025-2026.pdf" mengandung kedua tahun.

      - 2.0  → konten mengandung tahun yang ditanyakan (match kuat)
      - 0.4  → konten secara eksplisit menyebut HANYA tahun lain (penalty)
      - 1.0  → netral (tidak ada info tahun eksplisit di konten)
    """
    if not target_years:
        return 1.0

    content = (item.get("content") or "").lower()
    years_in_content = {int(y) for y in re.findall(r'\b(202[0-9])\b', content)}

    if not years_in_content:
        return 1.0  # Konten tidak menyebut tahun → netral

    target_set = set(target_years)
    if years_in_content & target_set:
        return 2.0  # Ada tahun yang cocok → boost

    return 0.4  # Hanya tahun lain → penalty


def _compute_keyword_boost(item: dict, keywords: list[str]) -> float:
    """
    Boost tambahan berdasarkan kata kunci query yang muncul di konten.
    Setiap kata kunci yang cocok menambah +0.5 faktor (max 2.0x).
    """
    if not keywords:
        return 1.0

    content = (item.get("content") or "").lower()
    matches = sum(1 for kw in keywords if kw in content)

    if matches == 0:
        return 1.0

    # +50% per keyword yang cocok, dibatasi 2.0x
    return min(1.0 + 0.5 * matches, 2.0)


def _rerank_by_year(results, question: str):
    """
    Re-rank hasil retrieval dengan boost gabungan:
      final_score = rrf_score × year_boost × keyword_boost

    - year_boost   → naik jika tahun di konten cocok dengan query
    - keyword_boost → naik jika kata kunci query ada di konten chunk
    """
    target_years = _extract_years_from_query(question)
    keywords = _extract_query_keywords(question)

    # Jika tidak ada tahun maupun keyword signifikan, lewati re-ranking
    if not target_years and not keywords:
        return results

    logging.info(
        "Re-ranking aktif — tahun: %s, keywords: %s",
        target_years, keywords,
    )

    scored = []
    for row in results:
        item = dict(row._mapping)
        rrf_score = float(item.get("rrf_score") or 0.0)
        year_boost = _compute_year_boost(item, target_years)
        kw_boost = _compute_keyword_boost(item, keywords)
        final_score = rrf_score * year_boost * kw_boost
        scored.append((final_score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored]


def _format_page_range(page_start, page_end) -> str | None:
    if page_start is None and page_end is None:
        return None
    if page_start == page_end or page_end is None:
        return str(page_start)
    if page_start is None:
        return str(page_end)
    return f"{page_start}-{page_end}"


def _build_context(rows) -> str:
    context_blocks = []

    for index, row in enumerate(rows, start=1):
        item = row._mapping
        metadata = item.get("metadata_json") or {}
        source_file = item.get("source_file") or metadata.get("source") or "Tidak diketahui"
        page_info = item.get("pages") or _format_page_range(
            item.get("page_start"),
            item.get("page_end"),
        )
        section_path = item.get("section_path") or metadata.get("section_path")

        header_parts = [
            f"Chunk {index}",
            f"Sumber: {source_file}",
        ]

        if page_info:
            header_parts.append(f"Halaman: {page_info}")
        if item.get("doc_type"):
            header_parts.append(f"Jenis dokumen: {item.get('doc_type')}")
        if section_path:
            header_parts.append(f"Bagian: {section_path}")

        context_blocks.append(
            "\n".join(
                [
                    " | ".join(header_parts),
                    item.get("content") or "",
                ]
            )
        )

    return "\n\n---\n\n".join(context_blocks)


def _build_sources(rows) -> list[dict]:
    sources = []

    for row in rows:
        item = row._mapping
        metadata = item.get("metadata_json") or {}
        content = item.get("content") or ""
        cosine_sim = float(item.get("cosine_similarity") or 0.0)

        sources.append(
            {
                "id": item.get("id"),
                "source_file": item.get("source_file") or metadata.get("source"),
                "doc_type": item.get("doc_type"),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
                "pages": item.get("pages"),
                "chapter": item.get("chapter"),
                "section": item.get("section"),
                "subsection": item.get("subsection"),
                "section_path": item.get("section_path"),
                "preview": content[:500] + ("..." if len(content) > 500 else ""),
                "similarity": cosine_sim,
                "score": float(item.get("rrf_score") or 0.0),
                "metadata": metadata,
            }
        )

    return sources


def chat_rag(question: str, top_k: int, db: Session):
    start_time = time.time()

    total_chunks = db.execute(text("SELECT COUNT(*) FROM public.document_chunks")).scalar_one()
    if total_chunks == 0:
        return {
            "question": question,
            "answer": NO_CONTEXT_ANSWER,
            "sources": [],
        }

    embeddings_model = get_embeddings()
    query_vector = embeddings_model.embed_query(question)
    vector_str = _format_pgvector(query_vector)

    query = """
        WITH semantic_search AS (
            SELECT
                id,
                content,
                source_file,
                doc_type,
                page_start,
                page_end,
                pages,
                chapter,
                section,
                subsection,
                section_path,
                metadata AS metadata_json,
                1 - (embedding <=> CAST(:vector AS vector)) AS cosine_similarity,
                RANK() OVER (ORDER BY embedding <=> CAST(:vector AS vector)) AS rank
            FROM public.document_chunks
            ORDER BY embedding <=> CAST(:vector AS vector)
            LIMIT :top_k
        ),
        keyword_search AS (
            SELECT
                id,
                content,
                source_file,
                doc_type,
                page_start,
                page_end,
                pages,
                chapter,
                section,
                subsection,
                section_path,
                metadata AS metadata_json,
                NULL::float AS cosine_similarity,
                RANK() OVER (
                    ORDER BY ts_rank_cd(
                        to_tsvector('simple', content),
                        plainto_tsquery('simple', :query_text)
                    ) DESC
                ) AS rank
            FROM public.document_chunks
            WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', :query_text)
            ORDER BY ts_rank_cd(
                to_tsvector('simple', content),
                plainto_tsquery('simple', :query_text)
            ) DESC
            LIMIT :top_k
        )
        SELECT
            COALESCE(s.id, k.id) AS id,
            COALESCE(s.content, k.content) AS content,
            COALESCE(s.source_file, k.source_file) AS source_file,
            COALESCE(s.doc_type, k.doc_type) AS doc_type,
            COALESCE(s.page_start, k.page_start) AS page_start,
            COALESCE(s.page_end, k.page_end) AS page_end,
            COALESCE(s.pages, k.pages) AS pages,
            COALESCE(s.chapter, k.chapter) AS chapter,
            COALESCE(s.section, k.section) AS section,
            COALESCE(s.subsection, k.subsection) AS subsection,
            COALESCE(s.section_path, k.section_path) AS section_path,
            COALESCE(s.metadata_json, k.metadata_json) AS metadata_json,
            COALESCE(s.cosine_similarity, 0.0) AS cosine_similarity,
            (1.0 / (60 + COALESCE(s.rank, 10000))) +
            (1.0 / (60 + COALESCE(k.rank, 10000))) AS rrf_score
        FROM semantic_search s
        FULL OUTER JOIN keyword_search k ON s.id = k.id
        ORDER BY rrf_score DESC
        LIMIT :top_k
    """

    results = db.execute(
        text(query),
        {"vector": vector_str, "top_k": top_k, "query_text": question},
    ).fetchall()

    if not results:
        return {
            "question": question,
            "answer": NO_CONTEXT_ANSWER,
            "sources": [],
        }

    # Re-rank berdasarkan tahun yang disebutkan dalam pertanyaan
    results = _rerank_by_year(results, question)

    context_text = _build_context(results)
    answer = generate_answer(question=question, context=context_text)

    retrieval_time_ms = int((time.time() - start_time) * 1000)
    logging.info("RAG completed in %sms with %s chunks", retrieval_time_ms, len(results))

    return {
        "question": question,
        "answer": answer or NO_CONTEXT_ANSWER,
        "sources": _build_sources(results),
    }

