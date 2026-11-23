from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
import os

class LlamaConfig(BaseModel):
    engine: Literal["LLAMA_CPP"] = Field(default="LLAMA_CPP")
    model_name: str = Field(..., description="Llama model name")
    llama_model_path: str = Field(..., description="Path to the .gguf model file")
    llama_gpu_layers: int = Field(default=1, ge=0, description="Number of GPU layers")
    llama_context_size: int = Field(default=2048, ge=1, description="Context size")
    
    @field_validator('llama_model_path')
    @classmethod
    def validate_model_path(cls, v):
        if not v or not v.strip():
            raise ValueError("LLAMA_MODEL_PATH is not set")
        if not os.path.exists(v):
            raise ValueError(f"Model file does not exist: {v}")
        if not v.endswith('.gguf'):
            raise ValueError("The model file must have a .gguf extension")
        return v
