from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Text, primary_key=True, index=True)
    content = Column(Text, nullable=False)

    source_file = Column(Text, nullable=True)
    doc_type = Column(Text, nullable=True)

    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    pages = Column(Text, nullable=True)

    chapter = Column(Text, nullable=True)
    section = Column(Text, nullable=True)
    subsection = Column(Text, nullable=True)
    section_path = Column(Text, nullable=True)

    metadata_json = Column("metadata", JSONB, nullable=False)

    # Model embedding seperti intfloat/multilingual-e5-large menghasilkan embedding 1024 dimensi
    embedding = Column(Vector(1024), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())