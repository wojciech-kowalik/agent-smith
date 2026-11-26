"""
Local LLaMA engine (llama.cpp through LangChain).
"""

import os
import warnings
from dotenv import load_dotenv
from cli import console
from .client import LLMClient
from .llama_validation import LlamaConfig

PREPARING_MESSAGE = "🦙 Preparing the llama.cpp client..."


def create_llama_client() -> LLMClient:
    """Builds the local LLaMA client from environment variables (loads the GGUF model)."""
    load_dotenv()
    config = LlamaConfig(
        model_name=os.getenv('MODEL_NAME') or os.getenv('LLAMA_MODEL_NAME', 'llama-3.1-8b-instruct'),
        llama_model_path=os.getenv('LLAMA_MODEL_PATH', ''),
        llama_gpu_layers=os.getenv('LLAMA_GPU_LAYERS', '1'),
        llama_context_size=os.getenv('LLAMA_CONTEXT_SIZE', '2048')
    )
    console.print_info(PREPARING_MESSAGE)
    console.print_info(f"Loading LLaMA model from: {config.llama_model_path}")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # langchain-community sunset notice
            from langchain_community.chat_models import ChatLlamaCpp
        # llama-cpp-python applies the model's own chat template (e.g. Llama 3.1's)
        model = ChatLlamaCpp(
            model_path=config.llama_model_path,
            n_gpu_layers=config.llama_gpu_layers,
            n_ctx=config.llama_context_size,
            max_tokens=512,
            verbose=False,
        )
    except Exception as e:
        console.print_error(f"LLaMA model initialization error: {e}")
        hint = ""
        if str(config.llama_gpu_layers) != "0":
            hint = (" Hint: the model may not fit in free GPU memory (another program, e.g. LM Studio or "
                    "Ollama, can be holding it): close it, or lower LLAMA_GPU_LAYERS (0 = CPU only) "
                    "or LLAMA_CONTEXT_SIZE.")
        raise RuntimeError(f"Failed to initialize LLaMA model: {e}{hint}")

    def count_tokens(messages) -> int:
        # The model's own tokenizer (the generic LangChain counter would need `transformers`)
        text = " ".join(str(m.content) for m in messages)
        return len(model.client.tokenize(text.encode('utf-8')))

    ready = (f"✅ llama.cpp client ready to use (local model: {config.model_name}, "
             f"GPU layers: {config.llama_gpu_layers}, Context: {config.llama_context_size})")
    return LLMClient(model, config.model_name, ready, context_size=config.llama_context_size, token_counter=count_tokens,
                     count_answer_tokens=True)
