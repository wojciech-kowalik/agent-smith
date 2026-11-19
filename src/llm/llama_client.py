"""
Local LLaMA LLM Client Implementation
Encapsulates all local LLaMA model interactions using llama-cpp-python.
"""

import os
from typing import Optional, List, Any, Dict, Callable
from llama_cpp import Llama
from dotenv import load_dotenv
from cli import console
from .llama_validation import LlamaConfig

class LlamaChatSession:
    """
    Wrapper class that provides a chat session interface compatible with Gemini's interface.
    Manages conversation history and provides send_message() and get_history() methods.
    """
    
    def __init__(self, llama_model: Llama, system_instruction: str, history: Optional[List[Dict]] = None):
        """
        Initialize the LLaMA chat session.
        
        Args:
            llama_model: Initialized Llama model instance
            system_instruction: System prompt for the assistant
            history: Previous conversation history
        """
        self.llama_model = llama_model
        self.system_instruction = system_instruction
        self._history = history or []
        
    supports_streaming = True
    
    def send_message(self, text: str, on_token: Optional[Callable[[str], None]] = None) -> Any:
        """
        Sends a message to the LLaMA model and returns a response object.
        
        Args:
            text: User's message
            on_token: Optional callback called with each piece of text as the model
                generates it. When omitted, the whole answer is generated first.
            
        Returns:
            Response object with .text attribute containing the response
        """
        # Add user message to history
        user_message = {"role": "user", "parts": [{"text": text}]}
        self._history.append(user_message)
        
        # Build chat messages; llama-cpp-python applies the model's own chat template
        messages = self._build_messages_from_history()
        
        try:
            # Generate response using LLaMA
            if on_token:
                pieces = []
                for chunk in self.llama_model.create_chat_completion(
                    messages=messages,
                    max_tokens=512,
                    stream=True,
                ):
                    piece = chunk["choices"][0]["delta"].get("content")
                    if piece:
                        pieces.append(piece)
                        on_token(piece)
                response_text = "".join(pieces).strip()
            else:
                output = self.llama_model.create_chat_completion(
                    messages=messages,
                    max_tokens=512,
                )
                response_text = output["choices"][0]["message"]["content"].strip()
            
            # Add assistant response to history
            assistant_message = {"role": "model", "parts": [{"text": response_text}]}
            self._history.append(assistant_message)
            
            # Return response object compatible with Gemini interface
            return LlamaResponse(response_text)
            
        except Exception as e:
            console.print_error(f"Error while generating LLaMA response: {e}")
            # Return error response
            error_text = "Sorry, an error occurred while generating the response."
            assistant_message = {"role": "model", "parts": [{"text": error_text}]}
            self._history.append(assistant_message)
            return LlamaResponse(error_text)
    
    def get_history(self) -> List[Dict]:
        """Returns the current conversation history."""
        return self._history
    
    def _build_messages_from_history(self) -> List[Dict[str, str]]:
        """
        Builds a list of chat messages (system + history) in the OpenAI-style
        format expected by create_chat_completion.
        
        Returns:
            List of {"role": ..., "content": ...} dicts
        """
        messages = []
        
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        
        for message in self._history:
            role = "assistant" if message["role"] == "model" else "user"
            messages.append({"role": role, "content": message["parts"][0]["text"]})
        
        return messages


class LlamaResponse:
    """
    Response object that mimics the Gemini response interface.
    Provides a .text attribute containing the response text.
    """
    
    def __init__(self, text: str):
        self.text = text


class LlamaClient:
    """
    Encapsulates all local LLaMA model interactions.
    Provides a clean interface compatible with GeminiLLMClient.
    """
    
    def __init__(self, model_name: str, model_path: str, n_gpu_layers: int = 1, n_ctx: int = 2048):
        """
        Initialize the LLaMA client with explicit parameters.
        
        Args:
            model_name: Display name for the model
            model_path: Path to the GGUF model file
            n_gpu_layers: Number of layers to run on GPU
            n_ctx: Maximum context length
            
        Raises:
            ValueError: If model_path is empty or file doesn't exist
        """
        if not model_path:
            raise ValueError("Model path cannot be empty")
        
        if not os.path.exists(model_path):
            raise ValueError(f"Model file not found: {model_path}")
        
        self.model_name = model_name
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        
        # Initialize the model during construction
        self._llama_model = self._initialize_model()
    
    @staticmethod
    def preparing_for_use_message() -> str:
        """
        Returns a message indicating that LLaMA client is being prepared.
        
        Returns:
            Formatted preparation message string
        """
        return "🦙 Preparing the llama.cpp client..."
    
    @classmethod
    def from_environment(cls) -> 'LlamaClient':
        """
        Factory method that creates a LlamaClient instance from environment variables.
        
        Returns:
            LlamaClient instance initialized with environment variables
            
        Raises:
            ValueError: If model file is not found or configuration is invalid
        """
        load_dotenv()
    
        # Validation with Pydantic
        config = LlamaConfig(
            model_name=os.getenv('LLAMA_MODEL_NAME', 'llama-3.1-8b-instruct'),
            llama_model_path=os.getenv('LLAMA_MODEL_PATH'),
            llama_gpu_layers=int(os.getenv('LLAMA_GPU_LAYERS', '1')),
            llama_context_size=int(os.getenv('LLAMA_CONTEXT_SIZE', '2048'))
        )
        
        console.print_info(f"Loading LLaMA model from: {config.llama_model_path}")
        
        return cls(
            model_name=config.model_name,
            model_path=config.llama_model_path,
            n_gpu_layers=config.llama_gpu_layers,
            n_ctx=config.llama_context_size
        )
    
    def _initialize_model(self) -> Llama:
        """
        Initializes the LLaMA model.
        
        Returns:
            Initialized Llama model instance
            
        Raises:
            RuntimeError: If model initialization fails
        """
        try:
            console.print_info(f"Initializing LLaMA model: {self.model_name}")
            console.print_info(f"Path: {self.model_path}")
            console.print_info(f"Warstwy GPU: {self.n_gpu_layers}, Kontekst: {self.n_ctx}")
            
            return Llama(
                model_path=self.model_path,
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=self.n_ctx,
                verbose=False  # Reduce verbose output
            )
        except Exception as e:
            console.print_error(f"LLaMA model initialization error: {e}")
            raise RuntimeError(f"Failed to initialize LLaMA model: {e}")
    
    def create_chat_session(self, 
                          system_instruction: str, 
                          history: Optional[List[Dict]] = None,
                          thinking_budget: int = 0) -> LlamaChatSession:
        """
        Creates a new chat session with the specified configuration.
        
        Args:
            system_instruction: System role/prompt for the assistant
            history: Previous conversation history (optional)
            thinking_budget: Ignored for LLaMA (compatibility parameter)
            
        Returns:
            LlamaChatSession object
        """
        if not self._llama_model:
            raise RuntimeError("LLaMA model not initialized")
        
        return LlamaChatSession(
            llama_model=self._llama_model,
            system_instruction=system_instruction,
            history=history or []
        )
    
    def count_history_tokens(self, history: List[Dict]) -> int:
        """
        Counts tokens for the given conversation history.
        Note: This is an approximation since llama-cpp-python doesn't provide 
        direct token counting for conversations.
        
        Args:
            history: Conversation history
            
        Returns:
            Estimated token count
        """
        if not history:
            return 0
        
        try:
            # Build text from history
            text_parts = []
            for message in history:
                if "parts" in message and message["parts"]:
                    text_parts.append(message["parts"][0]["text"])
            
            full_text = " ".join(text_parts)
            
            # Use LLaMA's tokenizer to count tokens
            tokens = self._llama_model.tokenize(full_text.encode('utf-8'))
            return len(tokens)
            
        except Exception as e:
            console.print_error(f"Error while counting tokens: {e}")
            # Fallback: rough estimation (4 chars per token average)
            total_chars = sum(len(msg["parts"][0]["text"]) for msg in history if "parts" in msg and msg["parts"])
            return total_chars // 4
    
    def get_context_size(self) -> int:
        """Returns the configured context window size (LLAMA_CONTEXT_SIZE)."""
        return self.n_ctx
    
    def get_model_name(self) -> str:
        """Returns the currently configured model name."""
        return self.model_name
    
    def is_available(self) -> bool:
        """
        Checks if the LLM service is available and properly configured.
        
        Returns:
            True if model is properly initialized
        """
        return self._llama_model is not None
    
    def ready_for_use_message(self) -> str:
        """
        Returns a ready-to-use message with model info and parameters.
        
        Returns:
            Formatted message string for display
        """
        return f"✅ llama.cpp client ready to use (local model: {self.model_name}, GPU layers: {self.n_gpu_layers}, Context: {self.n_ctx}"
    
    @property
    def client(self):
        """
        Provides access to the underlying LLaMA model for backwards compatibility.
        This property should be used sparingly and eventually removed.
        """
        return self._llama_model
