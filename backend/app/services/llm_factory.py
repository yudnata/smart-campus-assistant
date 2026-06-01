from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def get_llm():
    """
    Mengembalikan instance LLM berdasarkan API Key yang tersedia di .env.
    Prioritas: Gemini -> OpenAI -> Local (mock/placeholder).
    """
    if settings.gemini_api_key:
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.2
        )
    elif settings.openai_api_key:
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.openai_api_key,
            temperature=0.2
        )
    else:
        # Fallback error / mock
        raise ValueError("Tidak ada API Key LLM yang dikonfigurasi di .env")
