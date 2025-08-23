import os
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  # This loads variables from the .env file into the environment


# Load environment variables

class Config:
    # Ollama Configuration
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11433")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    
    # Application Configuration
    APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT = int(os.getenv("APP_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # Vector Store Configuration
    VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./data/vector_store")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 256))
    print("CHUNK_SIZE =", CHUNK_SIZE)

    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
    
    # Upload Configuration
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./backend/uploads")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10485760))  # 10MB
    
    # Retrieval Configuration
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", 5))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.7))
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.VECTOR_STORE_PATH,
            cls.UPLOAD_DIR
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

# Initialize configuration
config = Config()
config.ensure_directories()