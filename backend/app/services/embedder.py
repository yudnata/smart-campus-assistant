from langchain_huggingface import HuggingFaceEmbeddings

# Initialize the embedding model locally
# intfloat/multilingual-e5-large is highly capable for English/Indonesian retrieval tasks.
# It outputs vectors of dimension 1024.
embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")

def get_embeddings():
    return embeddings
