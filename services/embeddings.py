from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any
import logging
from utils import config

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.model_name = config.config.EMBEDDING_MODEL
        self.device = config.config.EMBEDDING_DEVICE
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise
    
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        try:
            embeddings = self.model.encode(
                texts,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def encode_single_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.encode_texts([text])[0]
    
    def encode_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for document chunks"""
        if not chunks:
            return []
        
        try:
            # Extract texts from chunks
            texts = [chunk["text"] for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.encode_texts(texts)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                chunk["embedding"] = embeddings[i]
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error encoding chunks: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by the model"""
        if not self.model:
            return None
        return self.model.get_sentence_embedding_dimension()
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings"""
        # Normalize embeddings
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity
        return np.dot(embedding1, embedding2)
    
    def find_similar_texts(self, 
                          query_text: str, 
                          corpus_embeddings: np.ndarray,
                          corpus_texts: List[str],
                          top_k: int = None) -> List[Dict[str, Any]]:
        """Find most similar texts to query"""
        if top_k is None:
            top_k = config.TOP_K_RESULTS
        
        # Generate query embedding
        query_embedding = self.encode_single_text(query_text)
        
        # Calculate similarities
        similarities = []
        for i, corpus_embedding in enumerate(corpus_embeddings):
            sim_score = self.similarity(query_embedding, corpus_embedding)
            similarities.append({
                "index": i,
                "text": corpus_texts[i],
                "similarity": float(sim_score)
            })
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model"""
        if not self.model:
            return {
                "model_name": self.model_name,
                "loaded": False,
                "error": "Model not loaded"
            }
        
        return {
            "model_name": self.model_name,
            "loaded": True,
            "device": self.device,
            "embedding_dimension": self.get_embedding_dimension(),
            "max_sequence_length": getattr(self.model, 'max_seq_length', 'Unknown')
        }