from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import shutil
import os
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

@app.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and process a document"""
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
        
        # Process document in background
        background_tasks.add_task(process_document_background, str(file_path))
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "size": file.size,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

async def process_document_background(file_path: str):
    """Background task to process uploaded document"""
    try:
        logger.info(f"Processing document: {file_path}")
        
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
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        logger.info(f"Successfully processed document: {Path(file_path).name}")
        
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the document collection"""
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        top_k = request.top_k or config.TOP_K_RESULTS
        
        # Generate query embedding
        query_embedding = embedding_service.encode_single_text(question)
        
        # Search vector store
        search_results = vector_store.search(query_embedding, top_k=top_k)
        
        if not search_results:
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

@app.get("/documents")
async def list_documents():
    """List information about stored documents"""
    try:
        stats = vector_store.get_stats()
        
        # Get unique filenames from metadata
        filenames = set()
        file_stats = {}
        
        for metadata in vector_store.metadata:
            filename = metadata.get("metadata", {}).get("file_name", "Unknown")
            filenames.add(filename)
            
            if filename not in file_stats:
                file_stats[filename] = {
                    "filename": filename,
                    "chunks": 0,
                    "file_type": metadata.get("metadata", {}).get("file_type", "unknown")
                }
            file_stats[filename]["chunks"] += 1
        
        return {
            "total_documents": len(filenames),
            "total_chunks": stats["total_vectors"],
            "documents": list(file_stats.values())
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a specific document and its chunks"""
    try:
        deleted_count = vector_store.delete_by_filename(filename)
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "message": f"Deleted document: {filename}",
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=config.APP_HOST, 
        port=config.APP_PORT,
        log_level="info"
    )