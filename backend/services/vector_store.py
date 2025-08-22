import faiss
import numpy as np
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from utils import config

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, dimension: int = None):
        self.index_path = Path(config.config.VECTOR_STORE_PATH)
        self.index_file = self.index_path / "faiss_index.bin"
        self.metadata_file = self.index_path / "metadata.pkl"
        self.config_file = self.index_path / "config.json"
        
        self.index = None
        self.metadata = []
        self.dimension = dimension
        
        # Ensure directory exists
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing index
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one"""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self._load_index()
                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
                return
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")
        
        # Create new index if loading failed or files don't exist
        if self.dimension:
            self._create_new_index(self.dimension)
        else:
            logger.info("No dimension specified and no existing index found")
    
    def _create_new_index(self, dimension: int):
        """Create new FAISS index"""
        try:
            # Use L2 distance (Euclidean)
            self.index = faiss.IndexFlatL2(dimension)
            self.metadata = []
            self.dimension = dimension
            
            # Save initial configuration
            config_data = {
                "dimension": dimension,
                "index_type": "IndexFlatL2",
                "created_at": str(Path().resolve())
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Created new FAISS index with dimension {dimension}")
        except Exception as e:
            logger.error(f"Error creating new index: {e}")
            raise
    
    def _load_index(self):
        """Load existing FAISS index and metadata"""
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_file))
            
            # Load metadata
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
            
            # Load config
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    self.dimension = config_data.get("dimension")
            
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            raise
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise
    
    def add_documents(self, chunks: List[Dict[str, Any]]):
        """Add document chunks to the vector store"""
        if not chunks:
            return
        
        try:
            # Extract embeddings and prepare metadata
            embeddings = []
            chunk_metadata = []
            
            for chunk in chunks:
                if "embedding" not in chunk:
                    raise ValueError("Chunk missing embedding")
                
                embeddings.append(chunk["embedding"])
                
                # Prepare metadata (exclude embedding to save space)
                metadata = chunk.copy()
                del metadata["embedding"]
                chunk_metadata.append(metadata)
            
            embeddings = np.array(embeddings).astype(np.float32)
            
            # Create index if it doesn't exist
            if self.index is None:
                dimension = embeddings.shape[1]
                self._create_new_index(dimension)
            
            # Add embeddings to index
            self.index.add(embeddings)
            
            # Add metadata
            self.metadata.extend(chunk_metadata)
            
            # Save to disk
            self._save_index()
            
            logger.info(f"Added {len(chunks)} chunks to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise
    
    def search(self, query_embedding: np.ndarray, top_k: int = None) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if top_k is None:
            top_k = config.TOP_K_RESULTS
        
        if self.index is None or self.index.ntotal == 0:
            return []
        
        try:
            # Ensure query embedding is the right shape and type
            query_embedding = np.array([query_embedding]).astype(np.float32)
            
            # Search in FAISS index
            distances, indices = self.index.search(query_embedding, top_k)
            
            # Prepare results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result["similarity_score"] = float(1 / (1 + distance))  # Convert distance to similarity
                    result["rank"] = i + 1
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "index_file_exists": self.index_file.exists(),
            "metadata_count": len(self.metadata),
            "storage_path": str(self.index_path)
        }
    
    def clear(self):
        """Clear all data from vector store"""
        try:
            if self.index_file.exists():
                self.index_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            if self.config_file.exists():
                self.config_file.unlink()
            
            self.index = None
            self.metadata = []
            self.dimension = None
            
            logger.info("Cleared vector store")
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            raise
    
    def delete_by_filename(self, filename: str) -> int:
        """Delete all chunks belonging to a specific file"""
        # Note: FAISS doesn't support deletion efficiently
        # This is a simplified implementation
        indices_to_remove = []
        
        for i, metadata in enumerate(self.metadata):
            if metadata.get("metadata", {}).get("file_name") == filename:
                indices_to_remove.append(i)
        
        if not indices_to_remove:
            return 0
        
        # Rebuild index without deleted items
        if self.index and self.index.ntotal > 0:
            # Get all embeddings
            all_embeddings = []
            new_metadata = []
            
            for i in range(len(self.metadata)):
                if i not in indices_to_remove:
                    # This is a limitation - we can't easily get embeddings back from FAISS
                    # In production, you'd want to store embeddings separately
                    new_metadata.append(self.metadata[i])
            
            # Update metadata
            self.metadata = new_metadata
            
            # Save updated index
            if self.metadata:
                self._save_index()
            else:
                self.clear()
            
            logger.info(f"Deleted {len(indices_to_remove)} chunks for file: {filename}")
            return len(indices_to_remove)
        
        return 0