import streamlit as st
import requests
import json
from pathlib import Path
import time
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SKF Orbitbot - AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"  # Start with sidebar opened
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_input_key" not in st.session_state:
    st.session_state.chat_input_key = 0

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"

# Enhanced CSS with blue theme and better UX
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global styling */
* {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: #3d4149;
}

/* Main chat interface styling */
.main-container {
    max-width: 400px;
    margin: 0 auto;
    background: white;
    border-radius: 20px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    margin-top: 2rem;
    margin-bottom: 2rem;
}
.sidebar-card {
    display: none;
}
/* Chat message styling */
.user-message {
    background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);
    color: white;
    padding: 1.2rem 1.8rem;
    border-radius: 20px 20px 5px 20px;
    margin: 1rem 0;
    margin-left: 15%;
    margin-right: 15%;
    position: relative;
    box-shadow: 0 4px 15px rgba(25, 118, 210, 0.3);
    animation: slideInRight 0.3s ease-out;
}

.assistant-message {
    background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
    color: #333;
    padding: 1.2rem 1.8rem;
    border-radius: 20px 20px 20px 5px;
    margin: 1rem 0;
    margin-right: 15%;
    margin-left: 15%;
    position: relative;
    box-shadow: 0 4px 15px rgba(33, 150, 243, 0.2);
    animation: slideInLeft 0.3s ease-out;
    border: 1px solid #BBDEFB;
}

@keyframes slideInRight {
    from { transform: translateX(50px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes slideInLeft {
    from { transform: translateX(-50px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

/* Avatar styling */
.user-avatar {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #1976D2, #0D47A1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    position: absolute;
    right: -50px;
    top: 10px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    font-size: 16px;
}

.assistant-avatar {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #2196F3, #1976D2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    position: absolute;
    left: -50px;
    top: 10px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    font-size: 18px;
}

/* Sidebar styling with light blue background */
.css-1d391kg, [data-testid="stSidebar"] {
    background: ##282C35;
}

.css-1d391kg .css-1v0mbdj, [data-testid="stSidebar"] > div {
    background: ##282C35 !important;
}

/* Sidebar text styling - all white */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown div,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stText,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] label {
    color: white !important;
}

/* Sidebar metric styling */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.2) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    backdrop-filter: blur(10px);
}

[data-testid="stSidebar"] [data-testid="stMetricLabel"],
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: white !important;
}

/* Individual cards for sidebar sections */
.sidebar-card {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 15px;
    padding: 1.5rem;
    margin: 1rem 0;
    border: 1px solid rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.sidebar-header {
    background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%);
    padding: 1.5rem;
    margin: -1rem -1rem 1rem -1rem;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(13, 71, 161, 0.3);
}

.sidebar-title {
    color: white !important;
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
}

.sidebar-subtitle {
    color: rgba(255, 255, 255, 0.9) !important;
    font-size: 0.9rem;
    margin: 0.5rem 0 0 0;
}

/* Status styling */
.status-healthy {
    background: linear-gradient(135deg, #4CAF50, #45a049);
    border: none;
    color: white !important;
    padding: 0.8rem;
    border-radius: 12px;
    text-align: center;
    margin: 0.5rem 0;
    box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
    font-weight: 500;
}

.status-unhealthy {
    background: linear-gradient(135deg, #f44336, #d32f2f);
    border: none;
    color: white !important;
    padding: 0.8rem;
    border-radius: 12px;
    text-align: center;
    margin: 0.5rem 0;
    box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3);
    font-weight: 500;
}

/* Sidebar buttons styling */
[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(25, 118, 210, 0.3) !important;
    transition: all 0.3s ease !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(25, 118, 210, 0.4) !important;
}

/* File uploader in sidebar */
[data-testid="stSidebar"] .stFileUploader > div {
    border: 2px dashed rgba(255, 255, 255, 0.5) !important;
    border-radius: 15px;
    padding: 1.5rem;
    background: rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
}

[data-testid="stSidebar"] .stFileUploader > div:hover {
    border-color: rgba(255, 255, 255, 0.8) !important;
    background: rgba(255, 255, 255, 0.15);
}

[data-testid="stSidebar"] .stFileUploader label {
    color: white !important;
}

/* Sidebar slider styling */
[data-testid="stSidebar"] .stSlider > div > div > div > div {
    background-color: white !important;
}

[data-testid="stSidebar"] .stSlider > div > div > div > div > div {
    background-color: #282C35 !important;
}

/* Sidebar checkbox styling */
[data-testid="stSidebar"] .stCheckbox > label > div[data-testid="stWidgetLabel"] {
    color: white !important;
}

/* Source styling */
.source-container {
    background: #E3F2FD;
    border-left: 4px solid #1976D2;
    padding: 1.2rem;
    margin: 1rem 0;
    border-radius: 0 12px 12px 0;
    box-shadow: 0 2px 10px rgba(25, 118, 210, 0.1);
    transition: transform 0.2s ease;
    color: #333;
}

.source-container:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(25, 118, 210, 0.2);
}

.source-header {
    font-weight: 600;
    color: #1976D2;
    margin-bottom: 0.8rem;
    font-size: 0.95rem;
}

/* Welcome message */
.welcome-container {
    text-align: center;
    padding: 4rem 2rem;
    background: white;
    border-radius: 20px;
    color: #333;
    margin: 2rem 0;
    box-shadow: 0 15px 35px rgba(25, 118, 210, 0.1);
}

.welcome-title {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: #1976D2;
}

.welcome-subtitle {
    font-size: 1.2rem;
    margin-bottom: 0.5rem;
    color: #666;
}

.welcome-description {
    font-size: 1rem;
    color: #666;
    max-width: 600px;
    margin: 0 auto;
    line-height: 1.6;
}

/* Input styling with 15% margin */
.stTextInput > div > div > input {
    border-radius: 25px;
    border: 2px solid #1976D2;
    padding: 1rem 1.5rem;
    font-size: 1rem;
    background: white;
    color: #333;
    box-shadow: 0 4px 15px rgba(25, 118, 210, 0.1);
    transition: all 0.3s ease;
    height: 80px;
}

.stTextInput > div > div > input:focus {
    border-color: #0D47A1;
    box-shadow: 0 4px 20px rgba(13, 71, 161, 0.2);
}

.stTextInput > div > div > input::placeholder {
    color: #999;
}

/* Button styling */
.stButton > button {
    border-radius: 25px;
    border: none;
    padding: 0.8rem 2rem;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    color: white;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(25, 118, 210, 0.4);
    background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%);
}

.stButton > button[kind="secondary"] {
    background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
    color: #1976D2;
}

.stButton > button[kind="secondary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(187, 222, 251, 0.4);
}

/* Metrics styling */
[data-testid="stMetric"] {
    background: white;
    padding: 1rem;
    border-radius: 12px;
    border: 1px solid #E3F2FD;
    margin: 0.5rem 0;
    box-shadow: 0 4px 15px rgba(25, 118, 210, 0.1);
}

[data-testid="stMetricLabel"] {
    color: #1976D2;
}

[data-testid="stMetricValue"] {
    color: #333;
}

/* Hide default streamlit elements */
.stDeployButton {
    visibility: hidden;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

/* Loading animation */
.stSpinner {
    text-align: center;
}

.stSpinner > div {
    color: #1976D2;
}

/* Sidebar expander styling */
[data-testid="stSidebar"] .streamlit-expanderHeader {
    background: rgba(255, 255, 255, 0.2) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    backdrop-filter: blur(10px);
}

[data-testid="stSidebar"] .streamlit-expanderHeader:hover {
    background: rgba(255, 255, 255, 0.25) !important;
}

[data-testid="stSidebar"] .streamlit-expanderContent {
    background: rgba(255, 255, 255, 0.1) !important;
    border-radius: 0 0 10px 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-top: none !important;
}

/* Expander styling */
.streamlit-expanderHeader {
    background: rgba(25, 118, 210, 0.1);
    border-radius: 10px;
    border: 1px solid rgba(25, 118, 210, 0.2);
    color: #1976D2;
    font-weight: 600;
}

.streamlit-expanderContent {
    background: white;
    border-radius: 0 0 10px 10px;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #1976D2, #0D47A1);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #0D47A1, #1976D2);
}

/* Chat input container with 15% margins */
.chat-input-container {
    position: fixed;
    bottom: 0;
    left: 15%;
    right: 15%;
    background: white;
    padding: 1rem;
    box-shadow: 0 -5px 15px rgba(0, 0, 0, 0.1);
    z-index: 999;
    border-radius: 20px 20px 0 0;
    display: none;
}

/* Example questions */
.example-questions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    flex-wrap: wrap;
}

.example-question {
    background: #E3F2FD;
    color: #1976D2;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 1px solid #BBDEFB;
}

.example-question:hover {
    background: #BBDEFB;
    transform: translateY(-2px);
}

/* Sidebar toggle button */
.sidebar-toggle {
    position: fixed;
    top: 1rem;
    left: 1rem;
    z-index: 1000;
    background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);
    border: none;
    border-radius: 50%;
    width: 50px;
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.2rem;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(25, 118, 210, 0.3);
    transition: all 0.3s ease;
}

.sidebar-toggle:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 20px rgba(25, 118, 210, 0.4);
}
</style>
""", unsafe_allow_html=True)

def check_api_health():
    """Check if the API is running and healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"API returned status {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def upload_file(file):
    """Upload a file to the API"""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"Upload failed with status {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def query_documents(question, top_k=5):
    """Query the document collection"""
    try:
        data = {"question": question, "top_k": top_k}
        response = requests.post(
            f"{API_BASE_URL}/query", 
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"Query failed with status {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def get_documents():
    """Get list of stored documents"""
    try:
        response = requests.get(f"{API_BASE_URL}/documents", timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"Failed to fetch documents: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def delete_document(filename):
    """Delete a document"""
    try:
        response = requests.delete(f"{API_BASE_URL}/documents/{filename}", timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"Failed to delete document: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def render_message(message, is_user=True):
    """Render a chat message with proper styling"""
    if is_user:
        st.markdown(f"""
        <div class="user-message">
            <div class="user-avatar">👤</div>
            {message}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="assistant-message">
            <div class="assistant-avatar">🤖</div>
            {message}
        </div>
        """, unsafe_allow_html=True)

def render_sources(sources):
    """Render source information"""
    if sources:
        st.markdown("### 📚 **Source References**")
        for i, source in enumerate(sources, 1):
            with st.expander(f"🔍 **Source {i}:** {source.get('file_name', 'Unknown')} | Relevance: {source.get('similarity_score', 0):.1%}", expanded=False):
                st.markdown(f"""
                <div class="source-container">
                    <div class="source-header">📄 Document Section #{source.get('chunk_id', 'N/A')}</div>
                    <div style="line-height: 1.6;">
                        {source['text']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

def main():
    # Sidebar for document management and system status
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <div class="sidebar-title">🤖 SKF Orbitbot</div>
            <div class="sidebar-subtitle">Your Intelligent Document Assistant</div>
        </div>
        """, unsafe_allow_html=True)
        
        # System Status Section - Card 1
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("### ⚡ System Status")
        health_ok, health_data = check_api_health()
        
        if health_ok:
            st.markdown('<div class="status-healthy">🟢 Connected & Ready</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-unhealthy">🔴 Connection Failed</div>', unsafe_allow_html=True)
            st.error("🚫 Backend not accessible at http://127.0.0.1:8000")
            st.info("💡 Please start the backend server to continue")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Document Upload Section - Card 2
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("### 📤 Upload Documents")
        
        uploaded_file = st.file_uploader(
            "Drop your files here or browse",
            type=['pdf', 'docx', 'txt'],
            help="📋 Supported formats: PDF, DOCX, TXT files"
        )
        
        if uploaded_file is not None:
            st.markdown(f"**📄 {uploaded_file.name}**")
            st.caption(f"💾 Size: {uploaded_file.size:,} bytes")
            
            if st.button("🚀 Upload", type="primary", use_container_width=True, key="upload_btn"):
                with st.spinner("🔄 Processing document..."):
                    success, result = upload_file(uploaded_file)
                    if success:
                        st.success("✅ Successfully uploaded!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Upload failed")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Document Management Section - Card 3
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("### 📚 Knowledge Base")
        
        docs_ok, docs_data = get_documents()
        if docs_ok:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📄 Documents", docs_data.get("total_documents", 0))
            with col2:
                st.metric("🧩 Text Chunks", docs_data.get("total_chunks", 0))
            
            if docs_data.get("documents"):
                with st.expander("📋 **Document Library** (Click to expand)", expanded=True):
                    for doc in docs_data["documents"]:
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.markdown(f"**📄 {doc['filename']}**")
                                st.caption(f"🧩 {doc['chunks']} chunks processed")
                            with col2:
                                if st.button("🗑️", key=f"del_{doc['filename']}", help="Delete document", use_container_width=True):
                                    with st.spinner("Deleting..."):
                                        success, result = delete_document(doc['filename'])
                                        if success:
                                            st.success("🗑️ Deleted!")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("❌ Delete failed")
                            st.markdown("---")  # Add separator between documents
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Settings Section - Card 4
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Assistant Settings")
        top_k = st.slider("🔍 Sources per response", 1, 10, 5, help="Number of document sources to reference")
        show_sources = st.checkbox("📚 Show source references", value=True, help="Display document sources used in responses")
        
        # Clear chat button
        if st.button("🧹 Clear Conversation", type="secondary", help="Start a fresh conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_input_key += 1
            st.success("🗑️ Conversation cleared!")
            time.sleep(1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main chat interface
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Welcome message when no conversation exists
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-container">
            <div class="welcome-title">🤖 SKF Orbitbot</div>
            <div class="welcome-subtitle">Your Advanced AI Document Assistant</div>
            <div class="welcome-description">
                Hello! I'm Orbitbot, your intelligent document companion. I can help you explore, analyze, 
                and extract insights from your uploaded documents. Upload your files using the sidebar and 
                start asking questions!
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick start tips
        st.markdown("### 🚀 Quick Start Guide")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📤 Step 1: Upload**
            - Use the sidebar to upload your documents
            - Supported: PDF, DOCX, TXT files
            - Files are automatically processed
            """)
        
        with col2:
            st.markdown("""
            **💭 Step 2: Ask Questions**
            - Type your questions in the chat below
            - Ask about content, summaries, insights
            - Reference specific topics or sections
            """)
        
        with col3:
            st.markdown("""
            **🎯 Step 3: Get Answers**
            - Receive AI-powered responses
            - View source references
            - Continue the conversation naturally
            """)
        
        # Example questions
        st.markdown("### 💡 Example Questions")
        examples = [
            "What is this document about?",
            "Summarize the key findings",
            "What are the main recommendations?",
            "Explain the technical details",
            "What problems does this solve?"
        ]
        
        cols = st.columns(3)
        for i, example in enumerate(examples):
            with cols[i % 3]:
                if st.button(example, key=f"ex_{i}", use_container_width=True):
                    st.session_state.chat_input_key += 1
                    st.session_state.example_question = example
                    st.rerun()
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            render_message(message["content"], is_user=True)
        else:
            render_message(message["content"], is_user=False)
            # Show sources if available
            if show_sources and "sources" in message:
                render_sources(message["sources"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input at the bottom with 15% margins
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    
    # Handle example question if set
    if "example_question" in st.session_state:
        default_question = st.session_state.example_question
        del st.session_state.example_question
    else:
        default_question = ""
    
    # Fixed input area at bottom
    user_input = st.text_input(
        "Message",
        value=default_question,
        placeholder="💬 Ask Orbitbot anything about your documents...",
        key=f"chat_input_{st.session_state.chat_input_key}",
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        send_button = st.button("🚀 Send", type="primary", disabled=not user_input.strip(), use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle user input
    if send_button and user_input.strip():
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get response from API
        with st.spinner("🧠 Orbitbot is thinking..."):
            success, result = query_documents(user_input.strip(), top_k)
            
            if success:
                # Add assistant response to chat history
                assistant_message = {
                    "role": "assistant", 
                    "content": result["answer"]
                }
                if result.get("sources"):
                    assistant_message["sources"] = result["sources"]
                
                st.session_state.messages.append(assistant_message)
            else:
                # Add error message
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"🚫 **Oops!** I encountered an issue: {result.get('error', 'Unknown error')}\n\nPlease try again or check if your documents are properly uploaded."
                })
        
        # Increment input key to reset the input field
        st.session_state.chat_input_key += 1
        st.rerun()

if __name__ == "__main__":
    main()