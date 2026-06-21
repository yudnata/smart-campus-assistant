from app.services.groq_service import get_groq_client


def get_llm():
    """
    Backward-compatible helper untuk kode lama.
    LLM utama proyek ini sekarang memakai Groq SDK resmi.
    """
    return get_groq_client()
