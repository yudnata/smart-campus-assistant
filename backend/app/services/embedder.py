from langchain_huggingface import HuggingFaceEmbeddings

# Initialize the embedding model locally
# all-MiniLM-L6-v2 is fast, lightweight, and standard for English/Indonesian general retrieval tasks.
# It outputs vectors of dimension 384.
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def get_embeddings():
    return embeddings
