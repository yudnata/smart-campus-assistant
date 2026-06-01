from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    # Using JSONB for flexible metadata (e.g., {"source": "pdf", "page": 1} or {"source": "web", "url": "..."})
    metadata_ = Column("metadata", JSONB, default={})
    # Sentence-transformers usually output 384 dimensions (all-MiniLM-L6-v2)
    # If using OpenAI embeddings, it's 1536. We will set it to 384 for default local models.
    embedding = Column(Vector(384))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
