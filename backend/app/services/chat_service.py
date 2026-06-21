import logging
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embedder import get_embeddings
from app.services.groq_service import generate_answer

logging.basicConfig(level=logging.INFO)

NO_CONTEXT_ANSWER = "Informasi tersebut tidak ditemukan di dokumen yang tersedia."


def _format_pgvector(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


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
                "preview": content[:180] + ("..." if len(content) > 180 else ""),
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

    context_text = _build_context(results)
    answer = generate_answer(question=question, context=context_text)

    retrieval_time_ms = int((time.time() - start_time) * 1000)
    logging.info("RAG completed in %sms with %s chunks", retrieval_time_ms, len(results))

    return {
        "question": question,
        "answer": answer or NO_CONTEXT_ANSWER,
        "sources": _build_sources(results),
    }

