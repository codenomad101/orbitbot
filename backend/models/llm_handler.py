import ollama
import httpx
from typing import List, Dict, Any
from utils import config

class LLMHandler:
    def __init__(self):
        self.client = ollama.Client(host=config.config.OLLAMA_HOST)
        self.model = config.config.OLLAMA_MODEL

    async def generate_response(self, prompt: str, context: List[str] = None) -> str:
        """Generate response using LLAMA model with optional context"""
        try:
            # Prepare the prompt with context if provided
            if context:
                context_text = "\n\n".join(context)
                full_prompt = f"""
Context information:
{context_text}

Question: {prompt}

Based on the context provided above, please answer the question. If the answer cannot be found in the context, please say so.

Answer:"""
            else:
                full_prompt = prompt
            
            # Generate response using Ollama
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': full_prompt
                    }
                ]
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"Sorry, I encountered an error while generating the response: {str(e)}"
    
    async def test_connection(self) -> bool:
        """Test if Ollama service is available"""
        try:
            # Try to list available models
            models = self.client.list()
            return True
        except Exception as e:
            print(f"Ollama connection test failed: {e}")
            return False
    
    async def generate_embedding_prompt(self, text: str) -> str:
        """Generate embeddings using the LLM (if supported)"""
        # Note: Not all models support embeddings directly
        # This is a placeholder for future implementation
        return text
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        try:
            models = self.client.list()
            current_model = None
            for model in models.get('models', []):
                if model['name'] == self.model:
                    current_model = model
                    break
            return {
                "model_name": self.model,
                "available": current_model is not None,
                "model_info": current_model
            }
        except Exception as e:
            return {
                "model_name": self.model,
                "available": False,
                "error": str(e)
            }