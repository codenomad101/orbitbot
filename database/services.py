from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .models import User, Document, DocumentChunk, SearchQuery, DocumentAccess, SystemLog

logger = logging.getLogger(__name__)

class UserService:
    """Service for user operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, username: str, email: str, hashed_password: str, role: str = "user") -> Optional[User]:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = self.get_user_by_username(username)
            if existing_user:
                return None
            
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                role=role
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            self.db.rollback()
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        return self.db.query(User).all()
    
    def update_user_role(self, user_id: int, role: str) -> bool:
        """Update user role"""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                user.role = role
                user.updated_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            self.db.rollback()
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user"""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                user.is_active = False
                user.updated_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            self.db.rollback()
            return False
    
    def update_last_login(self, user_id: int):
        """Update user's last login time"""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                user.last_login = datetime.utcnow()
                self.db.commit()
        except Exception as e:
            logger.error(f"Error updating last login: {e}")

class DocumentService:
    """Service for document operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_document(self, filename: str, original_filename: str, file_type: str, 
                       file_size: int, upload_path: str, uploaded_by: int) -> Optional[Document]:
        """Create a new document record"""
        try:
            document = Document(
                filename=filename,
                original_filename=original_filename,
                file_type=file_type,
                file_size=file_size,
                upload_path=upload_path,
                uploaded_by=uploaded_by,
                processing_status="pending"
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            self.db.rollback()
            return None
    
    def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    def get_document_by_filename(self, filename: str) -> Optional[Document]:
        """Get document by filename"""
        return self.db.query(Document).filter(Document.filename == filename).first()
    
    def get_all_documents(self) -> List[Document]:
        """Get all documents"""
        return self.db.query(Document).order_by(desc(Document.created_at)).all()
    
    def get_user_documents(self, user_id: int) -> List[Document]:
        """Get documents uploaded by a specific user"""
        return self.db.query(Document).filter(Document.uploaded_by == user_id).order_by(desc(Document.created_at)).all()
    
    def update_document_status(self, document_id: int, status: str, error: str = None) -> bool:
        """Update document processing status"""
        try:
            document = self.get_document_by_id(document_id)
            if document:
                document.processing_status = status
                if error:
                    document.processing_error = error
                document.updated_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating document status: {e}")
            self.db.rollback()
            return False
    
    def update_document_chunks(self, document_id: int, total_chunks: int) -> bool:
        """Update document chunk count"""
        try:
            document = self.get_document_by_id(document_id)
            if document:
                document.total_chunks = total_chunks
                document.updated_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating document chunks: {e}")
            self.db.rollback()
            return False
    
    def delete_document(self, document_id: int) -> bool:
        """Delete a document and its chunks"""
        try:
            document = self.get_document_by_id(document_id)
            if document:
                # Delete associated chunks first
                self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
                self.db.delete(document)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self.db.rollback()
            return False

class SearchService:
    """Service for search operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_search_query(self, user_id: int, query_text: str, document_id: int = None) -> Optional[SearchQuery]:
        """Create a new search query record"""
        try:
            search_query = SearchQuery(
                user_id=user_id,
                document_id=document_id,
                query_text=query_text
            )
            self.db.add(search_query)
            self.db.commit()
            self.db.refresh(search_query)
            return search_query
        except Exception as e:
            logger.error(f"Error creating search query: {e}")
            self.db.rollback()
            return None
    
    def update_search_response(self, query_id: int, response_text: str, sources_used: List[Dict], response_time_ms: int) -> bool:
        """Update search query with response"""
        try:
            query = self.db.query(SearchQuery).filter(SearchQuery.id == query_id).first()
            if query:
                query.response_text = response_text
                query.sources_used = sources_used
                query.response_time_ms = response_time_ms
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating search response: {e}")
            self.db.rollback()
            return False
    
    def get_user_search_history(self, user_id: int, limit: int = 50) -> List[SearchQuery]:
        """Get user's search history"""
        return self.db.query(SearchQuery).filter(
            SearchQuery.user_id == user_id
        ).order_by(desc(SearchQuery.created_at)).limit(limit).all()
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search statistics"""
        total_queries = self.db.query(SearchQuery).count()
        recent_queries = self.db.query(SearchQuery).filter(
            SearchQuery.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        return {
            "total_queries": total_queries,
            "queries_today": recent_queries
        }

class LogService:
    """Service for system logging"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_log(self, action: str, user_id: int = None, resource_type: str = None, 
                   resource_id: int = None, details: Dict = None, ip_address: str = None, 
                   user_agent: str = None) -> bool:
        """Create a system log entry"""
        try:
            log_entry = SystemLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(log_entry)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating log entry: {e}")
            self.db.rollback()
            return False
    
    def get_user_logs(self, user_id: int, limit: int = 100) -> List[SystemLog]:
        """Get logs for a specific user"""
        return self.db.query(SystemLog).filter(
            SystemLog.user_id == user_id
        ).order_by(desc(SystemLog.created_at)).limit(limit).all()
    
    def get_system_logs(self, limit: int = 100) -> List[SystemLog]:
        """Get system logs"""
        return self.db.query(SystemLog).order_by(desc(SystemLog.created_at)).limit(limit).all()

