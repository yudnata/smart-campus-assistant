import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def list_groq_models():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY is not set.")
        return
        
    client = Groq(api_key=api_key)
    try:
        models = client.models.list()
        print("Supported Groq Models:")
        for model in models.data:
            print("- ", model.id)
    except Exception as e:
        print("Failed to list models:", e)

if __name__ == "__main__":
    list_groq_models()
