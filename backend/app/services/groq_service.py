from functools import lru_cache

from groq import Groq

from app.core.config import settings


SYSTEM_PROMPT = """
Anda adalah asisten akademik untuk sistem RAG.
Jawab HANYA berdasarkan konteks dokumen yang diberikan.
Jika konteks tidak cukup atau informasi tidak ditemukan dalam dokumen, katakan secara jujur:
"Informasi tersebut tidak ditemukan di dokumen yang tersedia."
Jangan menggunakan pengetahuan umum, asumsi, atau membuat detail baru.
Gunakan bahasa Indonesia yang jelas, faktual, ringkas, dan profesional.
Sertakan rujukan sumber secara natural bila tersedia dari konteks.
""".strip()


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY belum dikonfigurasi di file .env")

    return Groq(api_key=settings.groq_api_key)


def generate_answer(question: str, context: str) -> str:
    client = get_groq_client()

    user_prompt = f"""
KONTEKS DOKUMEN:
{context}

PERTANYAAN:
{question}

Tulis jawaban akhir berdasarkan konteks dokumen di atas.
""".strip()

    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        top_p=1,
        max_tokens=1024,
    )

    return completion.choices[0].message.content or ""
