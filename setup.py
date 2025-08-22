#!/usr/bin/env python3
"""
Setup script for LLAMA 4 RAG System
This script helps set up the environment and install dependencies
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, check=True):
    """Run a shell command"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, check=check)
    return result.returncode == 0

def create_directory_structure():
    """Create the required directory structure"""
    directories = [
        "backend/models",
        "backend/services", 
        "backend/utils",
        "backend/uploads",
        "frontend",
        "data/vector_store"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Create __init__.py files
    init_files = [
        "backend/__init__.py",
        "backend/models/__init__.py",
        "backend/services/__init__.py",
        "backend/utils/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        print(f"Created file: {init_file}")

def setup_virtual_environment():
    """Set up Python virtual environment"""
    venv_path = Path("rag-env")
    
    if not venv_path.exists():
        print("Creating virtual environment...")
        if not run_command(f"{sys.executable} -m venv rag-env"):
            print("Failed to create virtual environment")
            return False
    else:
        print("Virtual environment already exists")
    
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    # Determine pip command based on OS
    if os.name == 'nt':  # Windows
        pip_cmd = "rag-env\\Scripts\\pip"
        python_cmd = "rag-env\\Scripts\\python"
    else:  # Linux/Mac
        pip_cmd = "rag-env/bin/pip"
        python_cmd = "rag-env/bin/python"
    
    # Upgrade pip
    run_command(f"{pip_cmd} install --upgrade pip")
    
    # Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt"):
        print("Failed to install requirements")
        return False
    
    return True

def check_ollama():
    """Check if Ollama is installed and running"""
    print("Checking Ollama installation...")
    
    # Check if ollama command exists
    result = subprocess.run("ollama --version", shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Ollama is not installed or not in PATH")
        print("Please install Ollama from: https://ollama.ai")
        print("After installation, run: ollama pull llama2")
        return False
    else:
        print(f"✅ Ollama is installed: {result.stdout.strip()}")
        
        # Check if llama2 model is available
        model_result = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
        if "llama3" in model_result.stdout:
            print("✅ LLAMA3 model is available")
        else:
            print("⚠️ LLAMA3 model not found")
            print("Run: ollama pull llama3")
            return False
    
    return True

def create_sample_files():
    """Create sample configuration and test files"""
    
    # Create a sample test document
    sample_content = """
# Sample Document for RAG Testing

This is a sample document to test the RAG (Retrieval-Augmented Generation) system.

## About RAG Systems

RAG systems combine the power of information retrieval and language generation. 
They work by:

1. **Document Ingestion**: Processing and storing documents in a searchable format
2. **Query Processing**: Understanding user questions and finding relevant information
3. **Answer Generation**: Using retrieved context to generate accurate responses

## Key Components

- **Vector Database**: Stores document embeddings for similarity search
- **Embedding Model**: Converts text into numerical representations
- **Language Model**: Generates human-like responses based on context
- **Retrieval System**: Finds the most relevant information for queries

## Benefits

RAG systems provide several advantages:
- Access to up-to-date information
- Reduced hallucination in AI responses
- Transparent source attribution
- Domain-specific knowledge integration

This document can be used to test various aspects of the RAG system including 
document processing, embedding generation, similarity search, and answer generation.
"""
    
    sample_file = Path("data/sample_document.txt")
    sample_file.parent.mkdir(exist_ok=True)
    
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    print(f"Created sample document: {sample_file}")

def print_next_steps():
    """Print instructions for next steps"""
    print("\n" + "="*60)
    print("🎉 Setup completed successfully!")
    print("="*60)
    
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    
    if os.name == 'nt':  # Windows
        print("   .\\rag-env\\Scripts\\activate")
    else:  # Linux/Mac
        print("   source rag-env/bin/activate")
    
    print("\n2. Start Ollama (if not running):")
    print("   ollama serve")
    
    print("\n3. Start the backend API:")
    print("   cd backend")
    print("   python app.py")
    
    print("\n4. In another terminal, start the frontend:")
    print("   cd frontend")
    print("   streamlit run streamlit_app.py")
    
    print("\n5. Open your browser and go to:")
    print("   - API: http://127.0.0.1:8000")
    print("   - Frontend: http://localhost:8501")
    
    print("\n6. Test with the sample document:")
    print("   - Upload data/sample_document.txt")
    print("   - Ask: 'What are the benefits of RAG systems?'")
    
    print("\n📚 For more information, check README.md")

def main():
    """Main setup function"""
    print("🦙 LLAMA 4 RAG System Setup")
    print("="*40)
    
    try:
        # Create directory structure
        print("\n1. Creating directory structure...")
        create_directory_structure()
        
        # Setup virtual environment
        print("\n2. Setting up virtual environment...")
        if not setup_virtual_environment():
            return False
        
        # Install dependencies
        print("\n3. Installing dependencies...")
        if not install_dependencies():
            return False
        
        # Check Ollama
        print("\n4. Checking Ollama...")
        ollama_ok = check_ollama()
        
        # Create sample files
        print("\n5. Creating sample files...")
        create_sample_files()
        
        # Print next steps
        if ollama_ok:
            print_next_steps()
        else:
            print("\n⚠️ Setup completed with warnings.")
            print("Please install and configure Ollama before proceeding.")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)