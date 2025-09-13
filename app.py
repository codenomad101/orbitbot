from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import shutil
import os
import time
from pathlib import Path
import logging
from typing import List, Optional
import asyncio


# Local imports
from services.document_processor import DocumentProcessor
from services.embeddings import EmbeddingService
from services.vector_store import VectorStore
from models.llm_handler import LLMHandler
from utils.config import config

# Database imports
from database.config import init_database, check_database_connection, get_db
from database.services import UserService, DocumentService, SearchService, LogService
from database.models import User
from sqlalchemy.orm import Session

# Auth imports
from auth.db_auth_handler import get_auth_handler
from auth.models import UserCreate, UserLogin, UserResponse, Token, UserRoleUpdate, DocumentResponse, SearchQueryResponse
from auth.dependencies import get_current_active_user, get_admin_user, get_optional_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLAMA 4 RAG API",
    description="RAG system with LLAMA 4 for document Q&A",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instances
document_processor = None
embedding_service = None
vector_store = None
llm_handler = None

# Pydantic models
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    query: str

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global document_processor, embedding_service, vector_store, llm_handler
    
    try:
        logger.info("Initializing services...")
        
        # Initialize database
        logger.info("Initializing database...")
        if not check_database_connection():
            logger.error("Database connection failed!")
            raise Exception("Database connection failed")
        
        init_database()
        logger.info("Database initialized successfully")
        
        # Create default admin user
        from database.config import SessionLocal
        db = SessionLocal()
        try:
            auth_handler = get_auth_handler(db)
            auth_handler.create_default_admin()
        finally:
            db.close()
        
        # Initialize services
        document_processor = DocumentProcessor()
        embedding_service = EmbeddingService()
        
        # Get embedding dimension for vector store
        embedding_dim = embedding_service.get_embedding_dimension()
        vector_store = VectorStore(dimension=embedding_dim)
        
        llm_handler = LLMHandler()
        
        # Test LLM connection
        connection_ok = await llm_handler.test_connection()
        if not connection_ok:
            logger.warning("Could not connect to Ollama. Please ensure Ollama is running.")
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LLAMA 4 RAG API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if services are initialized
        services_status = {
            "document_processor": document_processor is not None,
            "embedding_service": embedding_service is not None,
            "vector_store": vector_store is not None,
            "llm_handler": llm_handler is not None
        }
        
        # Test LLM connection
        llm_connection = await llm_handler.test_connection() if llm_handler else False
        
        # Get vector store stats
        vector_stats = vector_store.get_stats() if vector_store else {}
        
        return {
            "status": "healthy",
            "services": services_status,
            "llm_connection": llm_connection,
            "vector_store_stats": vector_stats,
            "config": {
                "model": config.OLLAMA_MODEL,
                "embedding_model": config.EMBEDDING_MODEL
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Upload and process a document (Admin only)"""
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.txt'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Check file size
        if file.size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {config.MAX_FILE_SIZE} bytes"
            )
        
        # Save uploaded file
        file_path = Path(config.UPLOAD_DIR) / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create document record in database
        document_service = DocumentService(db)
        document = document_service.create_document(
            filename=file.filename,
            original_filename=file.filename,
            file_type=file_extension[1:],  # Remove the dot
            file_size=file.size,
            upload_path=str(file_path),
            uploaded_by=current_user.id
        )
        
        if not document:
            raise HTTPException(status_code=500, detail="Failed to create document record")
        
        # Process document in background
        background_tasks.add_task(process_document_background, str(file_path), document.id, db)
        
        # Log the upload
        log_service = LogService(db)
        log_service.create_log(
            action="document_uploaded",
            user_id=current_user.id,
            resource_type="document",
            resource_id=document.id,
            details={"filename": file.filename, "file_size": file.size}
        )
        
        return DocumentResponse.model_validate(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

async def process_document_background(file_path: str, document_id: int, db: Session):
    """Background task to process uploaded document"""
    try:
        logger.info(f"Processing document: {file_path}")
        
        # Update document status to processing
        document_service = DocumentService(db)
        document_service.update_document_status(document_id, "processing")
        
        # Process document
        result = document_processor.process_file(file_path)
        text = result["text"]
        metadata = result["metadata"]
        
        # Create chunks
        chunks = document_processor.chunk_text(text, metadata)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        chunks_with_embeddings = embedding_service.encode_chunks(chunks)
        logger.info("Generated embeddings for chunks")
        
        # Add to vector store
        vector_store.add_documents(chunks_with_embeddings)
        logger.info("Added chunks to vector store")
        
        # Update document status and chunk count
        document_service.update_document_status(document_id, "completed")
        document_service.update_document_chunks(document_id, len(chunks))
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        logger.info(f"Successfully processed document: {Path(file_path).name}")
        
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        # Update document status to failed
        document_service = DocumentService(db)
        document_service.update_document_status(document_id, "failed", str(e))

@app.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Query the document collection"""
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        top_k = request.top_k or config.TOP_K_RESULTS
        
        # Create search query record
        search_service = SearchService(db)
        search_query = search_service.create_search_query(current_user.id, question)
        
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = embedding_service.encode_single_text(question)
        
        # Search vector store
        search_results = vector_store.search(query_embedding, top_k=top_k)
        
        if not search_results:
            response_time = int((time.time() - start_time) * 1000)
            search_service.update_search_response(
                search_query.id,
                "I couldn't find any relevant information in the uploaded documents to answer your question.",
                [],
                response_time
            )
            
            return QueryResponse(
                answer="I couldn't find any relevant information in the uploaded documents to answer your question.",
                sources=[],
                query=question
            )
        
        # Extract context from search results
        context_texts = []
        sources = []
        
        for result in search_results:
            context_texts.append(result["text"])
            sources.append({
                "text": result["text"][:200] + "..." if len(result["text"]) > 200 else result["text"],
                "similarity_score": result.get("similarity_score", 0),
                "chunk_id": result.get("chunk_id", 0),
                "file_name": result.get("metadata", {}).get("file_name", "Unknown")
            })
        
        # Generate answer using LLM
        answer = await llm_handler.generate_response(question, context_texts)
        
        # Update search query with response
        response_time = int((time.time() - start_time) * 1000)
        search_service.update_search_response(search_query.id, answer, sources, response_time)
        
        # Log the query
        log_service = LogService(db)
        log_service.create_log(
            action="document_query",
            user_id=current_user.id,
            resource_type="search",
            resource_id=search_query.id,
            details={"query": question, "response_time_ms": response_time}
        )
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            query=question
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")

@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents(current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """List information about stored documents (Admin only)"""
    try:
        document_service = DocumentService(db)
        documents = document_service.get_all_documents()
        
        # Log the action
        log_service = LogService(db)
        log_service.create_log(
            action="documents_listed",
            user_id=current_user.id,
            resource_type="document"
        )
        
        return [DocumentResponse.model_validate(doc) for doc in documents]
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: int, 
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a specific document and its chunks (Admin only)"""
    try:
        document_service = DocumentService(db)
        document = document_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete from vector store
        deleted_count = vector_store.delete_by_filename(document.filename)
        
        # Delete from database
        success = document_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document from database")
        
        # Log the deletion
        log_service = LogService(db)
        log_service.create_log(
            action="document_deleted",
            user_id=current_user.id,
            resource_type="document",
            resource_id=document_id,
            details={"filename": document.filename, "chunks_deleted": deleted_count}
        )
        
        return {
            "message": f"Deleted document: {document.filename}",
            "chunks_deleted": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")

@app.get("/models/info")
async def get_model_info():
    """Get information about loaded models"""
    try:
        llm_info = llm_handler.get_model_info() if llm_handler else {}
        embedding_info = embedding_service.get_model_info() if embedding_service else {}
        
        return {
            "llm_model": llm_info,
            "embedding_model": embedding_info
        }
        
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=f"Model info error: {str(e)}")

# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        auth_handler = get_auth_handler(db)
        success = auth_handler.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )
        
        # Return user data without password
        new_user = auth_handler.get_user_by_username(user_data.username)
        return UserResponse.model_validate(new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token"""
    try:
        auth_handler = get_auth_handler(db)
        user = auth_handler.authenticate_user(user_credentials.username, user_credentials.password)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = auth_handler.create_access_token(
            data={"sub": user.id, "role": user.role}
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)

@app.get("/auth/users", response_model=List[UserResponse])
async def list_users(admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """List all users (admin only)"""
    try:
        auth_handler = get_auth_handler(db)
        users = auth_handler.get_all_users()
        return [UserResponse.model_validate(user) for user in users]
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing users: {str(e)}")

@app.put("/auth/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)"""
    try:
        auth_handler = get_auth_handler(db)
        success = auth_handler.update_user_role(user_id, role_update.role)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": f"User role updated to {role_update.role}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating user role: {str(e)}")

@app.put("/auth/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate a user (admin only)"""
    try:
        auth_handler = get_auth_handler(db)
        success = auth_handler.deactivate_user(user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": f"User has been deactivated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(status_code=500, detail=f"Error deactivating user: {str(e)}")

@app.post("/auth/users/create", response_model=UserResponse)
async def create_user_by_admin(
    user_data: UserCreate,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    try:
        auth_handler = get_auth_handler(db)
        success = auth_handler.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )
        
        # Return user data without password
        new_user = auth_handler.get_user_by_username(user_data.username)
        
        # Log the user creation by admin
        log_service = LogService(db)
        log_service.create_log(
            action="user_created_by_admin",
            user_id=admin_user.id,
            resource_type="user",
            resource_id=new_user.id,
            details={"created_user": user_data.username, "role": user_data.role}
        )
        
        return UserResponse.model_validate(new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"User creation error: {str(e)}")

# Additional endpoints for analytics and search history
@app.get("/search/history", response_model=List[SearchQueryResponse])
async def get_search_history(
    current_user: User = Depends(get_current_active_user),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get user's search history"""
    try:
        search_service = SearchService(db)
        queries = search_service.get_user_search_history(current_user.id, limit)
        return [SearchQueryResponse.model_validate(query) for query in queries]
        
    except Exception as e:
        logger.error(f"Error getting search history: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting search history: {str(e)}")

@app.get("/analytics/stats")
async def get_analytics_stats(admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Get system analytics (Admin only)"""
    try:
        search_service = SearchService(db)
        document_service = DocumentService(db)
        user_service = UserService(db)
        
        search_stats = search_service.get_search_stats()
        total_documents = len(document_service.get_all_documents())
        total_users = len(user_service.get_all_users())
        
        return {
            "search_stats": search_stats,
            "total_documents": total_documents,
            "total_users": total_users,
            "vector_store_stats": vector_store.get_stats() if vector_store else {}
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting analytics: {str(e)}")

@app.get("/logs/system")
async def get_system_logs(
    admin_user: User = Depends(get_admin_user),
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get system logs (Admin only)"""
    try:
        log_service = LogService(db)
        logs = log_service.get_system_logs(limit)
        
        return [
            {
                "id": log.id,
                "action": log.action,
                "user_id": log.user_id,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at
            }
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting system logs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=config.APP_HOST, 
        port=config.APP_PORT,
        log_level="info"
    )