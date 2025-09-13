from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # admin, user
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    search_queries = relationship("SearchQuery", back_populates="user")
    document_access = relationship("DocumentAccess", back_populates="user", foreign_keys="DocumentAccess.user_id")
    uploaded_documents = relationship("Document", foreign_keys="Document.uploaded_by")

class Document(Base):
    """Document model for storing document metadata"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, txt
    file_size = Column(Integer, nullable=False)
    upload_path = Column(String(500), nullable=True)
    processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Document processing metadata
    total_chunks = Column(Integer, default=0)
    processing_error = Column(Text, nullable=True)
    
    # Relationships
    uploader = relationship("User", back_populates="uploaded_documents", foreign_keys=[uploaded_by], overlaps="uploaded_documents")
    chunks = relationship("DocumentChunk", back_populates="document")
    search_queries = relationship("SearchQuery", back_populates="document")

class DocumentChunk(Base):
    """Document chunks for vector storage"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_metadata = Column(JSON, nullable=True)  # Store additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")

class SearchQuery(Base):
    """Search query history"""
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # If query was document-specific
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    sources_used = Column(JSON, nullable=True)  # Store source document info
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="search_queries")
    document = relationship("Document", back_populates="search_queries")

class DocumentAccess(Base):
    """Document access permissions"""
    __tablename__ = "document_access"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    access_type = Column(String(20), default="read")  # read, write, admin
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="document_access", foreign_keys=[user_id])
    document = relationship("Document")
    granter = relationship("User", foreign_keys=[granted_by])

class SystemLog(Base):
    """System logs for audit and debugging"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # login, upload, delete, etc.
    resource_type = Column(String(50), nullable=True)  # user, document, etc.
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
