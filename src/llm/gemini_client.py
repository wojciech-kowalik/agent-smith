"""
Google Gemini LLM Client Implementation
Encapsulates all Google Gemini AI interactions.
"""

import os
import sys
import threading
from typing import Optional, List, Any, Dict, Callable
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from dotenv import load_dotenv
from cli import console
from .gemini_validation import GeminiConfig

def _timeout_exceptions() -> tuple:
    """Timeout exception classes of the HTTP library used by google-genai (httpx2 by default, or httpx)."""
    classes = []
    for module_name in ("httpx2", "httpx"):
        try:
            classes.append(__import__(module_name).TimeoutException)
        except (ImportError, AttributeError):
            pass
    return tuple(classes)

TIMEOUT_EXCEPTIONS = _timeout_exceptions()


def _call_with_deadline(func: Callable[[], Any], timeout: Optional[float]) -> Any:
    """
    Runs func and waits at most `timeout` seconds in total (wall clock), no matter how
    many HTTP attempts, retries or slow streaming chunks happen inside it.

    Raises:
        TimeoutError: If func did not finish in time (its thread is abandoned)
    """
    if not timeout:
        return func()

    outcome: Dict[str, Any] = {}

    def worker():
        try:
            outcome["result"] = func()
        except BaseException as e:  # re-raised in the caller's thread
            outcome["error"] = e

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"No response within {timeout:g}s")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]

class GeminiChatSessionWrapper:
    """
    Wrapper for Gemini chat session that provides universal dictionary-based history format.
    This ensures compatibility with LlamaClient's history format.
    """
    
    def __init__(self, gemini_session, fallback_factory: Optional[Callable[[List[Dict]], Any]] = None,
                 model_name: str = "", fallback_model_name: str = "",
                 timeout: Optional[float] = None):
        """
        Initialize wrapper with Gemini chat session.
        
        Args:
            gemini_session: The actual Gemini chat session object
            fallback_factory: Optional callable that builds a session on the fallback model
                from the current history (universal dict format)
        """
        self.gemini_session = gemini_session
        self._fallback_factory = fallback_factory
        self._model_name = model_name
        self._fallback_model_name = fallback_model_name
        self._timeout = timeout
    
    def send_message(self, text: str) -> Any:
        """
        Forwards message to Gemini session.
        
        Args:
            text: User's message
            
        Returns:
            Response object from Gemini
        """
        try:
            return self._send_with_deadline(text)
        except (genai_errors.ServerError, TimeoutError, *TIMEOUT_EXCEPTIONS) as e:
            # Primary model timed out or still fails after the client's retries - switch to fallback
            if not self._fallback_factory:
                raise
            reason = "response time limit exceeded" if isinstance(e, (TimeoutError, *TIMEOUT_EXCEPTIONS)) \
                else f"server error {e.code}"
            console.print_info(
                f"⚠️ Model {self._model_name} did not respond ({reason}). "
                f"Switching to the fallback model: {self._fallback_model_name}..."
            )
            self.gemini_session = self._fallback_factory(self.get_history())
            self._fallback_factory = None  # switch only once per session
            return self._send_with_deadline(text)
    
    def _send_with_deadline(self, text: str) -> Any:
        """Sends a message, giving up after the total timeout (retries included)."""
        session = self.gemini_session
        return _call_with_deadline(lambda: session.send_message(text), self._timeout)
    
    def get_history(self) -> List[Dict]:
        """
        Gets conversation history in universal dictionary format.
        
        Returns:
            List of dictionaries with format: {"role": "user|model", "parts": [{"text": "..."}]}
        """
        gemini_history = self.gemini_session.get_history()
        universal_history = []
        
        for content in gemini_history:
            # Convert Gemini Content object to universal dictionary format
            text_part = ""
            if hasattr(content, 'parts') and content.parts:
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_part = part.text
                        break
            
            if text_part:
                universal_content = {
                    "role": content.role,
                    "parts": [{"text": text_part}]
                }
                universal_history.append(universal_content)
        
        return universal_history

class GeminiLLMClient:
    """
    Encapsulates all Google Gemini AI interactions.
    Provides a clean interface for chat sessions, token counting, and configuration.
    """
    
    def __init__(self, model_name: str, api_key: str, proxy_url: Optional[str] = None,
                 fallback_model_name: Optional[str] = None, timeout: Optional[float] = None):
        """
        Initialize the Gemini LLM client with explicit parameters.
        
        Args:
            model_name: Model to use (e.g., 'gemini-3.8-flash')
            api_key: Google Gemini API key
            proxy_url: Optional base URL of a proxy used instead of the default Gemini endpoint
            fallback_model_name: Optional model used when the main model times out or keeps returning server errors
            timeout: Optional per-request timeout in seconds (None = no timeout)
        
        Raises:
            ValueError: If api_key is empty or None
        """
        if not api_key:
            raise ValueError("API key cannot be empty or None")
        
        self.model_name = model_name
        self.api_key = api_key
        self.proxy_url = proxy_url
        self.fallback_model_name = fallback_model_name
        self.timeout = timeout
        
        # Initialize the client during construction
        self._client = self._initialize_client()
    
    @staticmethod
    def preparing_for_use_message() -> str:
        """
        Returns a message indicating that Gemini client is being prepared.
        
        Returns:
            Formatted preparation message string
        """
        return "🤖 Preparing the Gemini client..."
    
    @classmethod
    def from_environment(cls) -> 'GeminiLLMClient':
        """
        Factory method that creates a GeminiLLMClient instance from environment variables.
        
        Returns:
            GeminiLLMClient instance initialized with environment variables
            
        Raises:
            ValueError: If required environment variables are not set
        """
        load_dotenv()
    
        # Validation with Pydantic
        config = GeminiConfig(
            model_name=os.getenv('MODEL_NAME', 'gemini-3.8-flash'),
            gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
            gemini_proxy_url=os.getenv('GEMINI_PROXY_URL'),
            gemini_fallback_model=os.getenv('GEMINI_FALLBACK_MODEL'),
            gemini_timeout=os.getenv('GEMINI_TIMEOUT') or 30
        )
        
        return cls(
            model_name=config.model_name,
            api_key=config.gemini_api_key,
            proxy_url=config.gemini_proxy_url,
            fallback_model_name=config.gemini_fallback_model,
            timeout=config.gemini_timeout
        )
    
    def _initialize_client(self) -> genai.Client:
        """
        Initializes the Google GenAI client.
        
        Returns:
            Initialized GenAI client
            
        Raises:
            SystemExit: If client initialization fails
        """
        try:
            # Retry transient errors (rate limit / overload) with exponential backoff
            http_options = types.HttpOptions(
                base_url=self.proxy_url or None,
                timeout=int(self.timeout * 1000) if self.timeout else None,  # SDK expects milliseconds
                retry_options=types.HttpRetryOptions(
                    attempts=5,
                    initial_delay=1.0,
                    max_delay=30.0,
                    http_status_codes=[429, 500, 502, 503, 504],
                ),
            )
            return genai.Client(api_key=self.api_key, http_options=http_options)
        except Exception as e:
            console.print_error(f"Gemini client initialization error: {e}")
            sys.exit(1)
    
    def create_chat_session(self, 
                          system_instruction: str, 
                          history: Optional[List[Dict]] = None,
                          thinking_budget: int = 0) -> GeminiChatSessionWrapper:
        """
        Creates a new chat session with the specified configuration.
        
        Args:
            system_instruction: System role/prompt for the assistant
            history: Previous conversation history (optional, in universal dict format)
            thinking_budget: Thinking budget for the model
            
        Returns:
            GeminiChatSessionWrapper with universal dictionary-based interface
        """
        if not self._client:
            raise RuntimeError("LLM client not initialized")
        
        def build_session(model: str, hist: Optional[List[Dict]]):
            # Convert universal dict format to Gemini Content objects
            gemini_history = []
            for entry in hist or []:
                if isinstance(entry, dict) and 'role' in entry and 'parts' in entry:
                    text = entry['parts'][0].get('text', '') if entry['parts'] else ''
                    if text:
                        gemini_history.append(types.Content(
                            role=entry['role'],
                            parts=[types.Part.from_text(text=text)]
                        ))
            return self._client.chats.create(
                model=model,
                history=gemini_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget)
                )
            )
        
        fallback_factory = None
        if self.fallback_model_name and self.fallback_model_name != self.model_name:
            fallback_factory = lambda hist: build_session(self.fallback_model_name, hist)
        
        return GeminiChatSessionWrapper(
            build_session(self.model_name, history), fallback_factory,
            model_name=self.model_name, fallback_model_name=self.fallback_model_name or "",
            timeout=self.timeout
        )
    
    def count_history_tokens(self, history: List[Dict]) -> int:
        """
        Counts tokens for the given conversation history.
        
        Args:
            history: Conversation history in universal dict format
            
        Returns:
            Total token count
        """
        if not history:
            return 0
        
        try:
            # Convert universal dict format to Gemini Content objects for token counting
            gemini_history = []
            for entry in history:
                if isinstance(entry, dict) and 'role' in entry and 'parts' in entry:
                    text = entry['parts'][0].get('text', '') if entry['parts'] else ''
                    if text:
                        content = types.Content(
                            role=entry['role'],
                            parts=[types.Part.from_text(text=text)]
                        )
                        gemini_history.append(content)
            
            response = self._client.models.count_tokens(
                model=self.model_name,
                contents=gemini_history
            )
            return response.total_tokens
        except Exception as e:
            console.print_error(f"Error while counting tokens: {e}")
            return 0
    
    def get_model_name(self) -> str:
        """Returns the currently configured model name."""
        return self.model_name
    
    def is_available(self) -> bool:
        """
        Checks if the LLM service is available and properly configured.
        
        Returns:
            True if client is properly initialized and has API key
        """
        return self._client is not None and bool(self.api_key)
    
    def ready_for_use_message(self) -> str:
        """
        Returns a ready-to-use message with model info and masked API key.
        
        Returns:
            Formatted message string for display
        """
        # Mask API key - show first 4 and last 4 characters
        if len(self.api_key) <= 8:
            masked_key = "****"
        else:
            masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}"
        
        proxy_info = f", Proxy: {self.proxy_url}" if self.proxy_url else ""
        return f"✅ Gemini client ready to use (Model: {self.model_name}, Key: {masked_key}{proxy_info})"
    
    @property
    def client(self):
        """
        Provides access to the underlying GenAI client for backwards compatibility.
        This property should be used sparingly and eventually removed.
        """
        return self._client
