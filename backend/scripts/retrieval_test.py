from functools import lru_cache
import re

from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from app.core.database import SessionLocal


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def get_model():
    """
    Model hanya dimuat sekali agar retrieval lebih cepat.
    """
    return SentenceTransformer(MODEL_NAME)


def format_pgvector(vector: list[float]) -> str:
    """
    Mengubah list embedding Python menjadi format string vector PostgreSQL.
    Contoh: [0.1, 0.2, 0.3]
    """
    return "[" + ",".join(str(x) for x in vector) + "]"


def detect_calendar_filters(query: str) -> tuple[list[str], dict]:
    """
    Membuat filter tambahan khusus untuk data kalender.

    Tujuannya:
    - istilah penting seperti wisuda, UKT, KRS tetap dicocokkan secara keyword
    - angka seperti 175 tetap dicocokkan secara exact
    - setelah kandidat dipersempit, ranking tetap memakai semantic similarity
    """
    query_lower = query.lower()

    conditions = []
    params = {}

    # Filter untuk pertanyaan wisuda
    if "wisuda" in query_lower:
        conditions.append(
            "(content ILIKE :wisuda_keyword OR section_path ILIKE :wisuda_section)"
        )
        params["wisuda_keyword"] = "%wisuda%"
        params["wisuda_section"] = "%KKN DAN WISUDA%"

    # Filter untuk kata pendaftaran
    if "pendaftaran" in query_lower:
        conditions.append("content ILIKE :pendaftaran_keyword")
        params["pendaftaran_keyword"] = "%pendaftaran%"

    # Filter angka spesifik, misalnya 175, 176, 177
    number_match = re.search(r"\b(\d{3})\b", query_lower)
    if number_match:
        number = number_match.group(1)
        conditions.append("content ILIKE :number_keyword")
        params["number_keyword"] = f"%{number}%"

    # Filter untuk UKT
    if "ukt" in query_lower or "uang kuliah tunggal" in query_lower:
        conditions.append(
            "(content ILIKE :ukt_keyword OR content ILIKE :ukt_full_keyword)"
        )
        params["ukt_keyword"] = "%UKT%"
        params["ukt_full_keyword"] = "%Uang Kuliah Tunggal%"

    # Filter untuk KRS
    if "krs" in query_lower or "kartu rencana studi" in query_lower:
        conditions.append(
            "(content ILIKE :krs_keyword OR content ILIKE :krs_full_keyword)"
        )
        params["krs_keyword"] = "%KRS%"
        params["krs_full_keyword"] = "%Kartu Rencana Studi%"

    # Filter untuk cuti akademik pada kalender
    if "cuti" in query_lower:
        conditions.append("content ILIKE :cuti_keyword")
        params["cuti_keyword"] = "%cuti%"

    return conditions, params


def build_search_sql(where_conditions: list[str]) -> str:
    """
    Membuat SQL retrieval secara dinamis.
    """
    where_clause = ""

    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    sql = f"""
        SELECT
            id,
            content,
            source_file,
            doc_type,
            pages,
            section_path,
            1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
        FROM document_chunks
        {where_clause}
        ORDER BY embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k;
    """

    return sql


def search_chunks(
    query: str,
    top_k: int = 5,
    doc_type: str | None = None,
):
    model = get_model()

    query_embedding = model.encode(
        query,
        normalize_embeddings=True,
    ).tolist()

    query_embedding = format_pgvector(query_embedding)

    db = SessionLocal()

    try:
        where_conditions = []
        params = {
            "query_embedding": query_embedding,
            "top_k": top_k,
        }

        # Filter metadata berdasarkan tipe dokumen
        if doc_type:
            where_conditions.append("doc_type = :doc_type")
            params["doc_type"] = doc_type

        # Filter tambahan khusus kalender akademik
        calendar_conditions = []
        calendar_params = {}

        if doc_type == "kalender_akademik":
            calendar_conditions, calendar_params = detect_calendar_filters(query)
            where_conditions.extend(calendar_conditions)
            params.update(calendar_params)

        sql = text(build_search_sql(where_conditions))
        results = db.execute(sql, params).fetchall()

        # Fallback:
        # Kalau filter keyword terlalu ketat dan tidak menghasilkan apa-apa,
        # ulangi pencarian dengan filter doc_type saja.
        if not results and calendar_conditions:
            fallback_conditions = []
            fallback_params = {
                "query_embedding": query_embedding,
                "top_k": top_k,
            }

            if doc_type:
                fallback_conditions.append("doc_type = :doc_type")
                fallback_params["doc_type"] = doc_type

            fallback_sql = text(build_search_sql(fallback_conditions))
            results = db.execute(fallback_sql, fallback_params).fetchall()

        return results

    finally:
        db.close()


if __name__ == "__main__":
    test_questions = [
        {
            "query": "kapan pembayaran UKT semester genap?",
            "doc_type": "kalender_akademik",
        },
        {
            "query": "bagaimana tata cara pengajuan cuti akademik?",
            "doc_type": "pedoman_akademik",
        },
        {
            "query": "berapa lama masa studi mahasiswa sarjana?",
            "doc_type": "pedoman_akademik",
        },
        {
            "query": "kapan pendaftaran wisuda ke-175?",
            "doc_type": "kalender_akademik",
        },
    ]

    for item in test_questions:
        query = item["query"]
        doc_type = item["doc_type"]

        print("=" * 100)
        print(f"QUERY    : {query}")
        print(f"DOC TYPE : {doc_type}")

        results = search_chunks(
            query=query,
            top_k=5,
            doc_type=doc_type,
        )

        for index, row in enumerate(results, start=1):
            print("-" * 100)
            print(f"Rank       : {index}")
            print(f"Similarity : {row.similarity:.4f}")
            print(f"Doc Type   : {row.doc_type}")
            print(f"Source     : {row.source_file}")
            print(f"Pages      : {row.pages}")
            print(f"Section    : {row.section_path}")
            print()
            print(row.content[:500])
            print()