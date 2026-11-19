from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

class GeminiConfig(BaseModel):
    engine: Literal["GEMINI"] = Field(default="GEMINI")
    model_name: str = Field(..., description="Gemini model name")
    gemini_api_key: str = Field(..., min_length=1, description="Google Gemini API key")
    gemini_proxy_url: Optional[str] = Field(default=None, description="Optional proxy URL for the Gemini API")
    gemini_fallback_model: Optional[str] = Field(default=None, description="Optional fallback Gemini model")
    gemini_timeout: Optional[float] = Field(default=30, gt=0, description="Model response time limit (in seconds)")
    
    @field_validator('gemini_fallback_model')
    @classmethod
    def validate_fallback_model(cls, v):
        return (v or "").strip() or None
    
    @field_validator('gemini_proxy_url')
    @classmethod
    def validate_proxy_url(cls, v):
        v = (v or "").strip()
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("GEMINI_PROXY_URL must start with http:// or https://")
        return v
    
    @field_validator('gemini_api_key')
    @classmethod
    def validate_api_key(cls, v):
        if not v or v.strip() == "":
            raise ValueError("GEMINI_API_KEY cannot be empty")
        return v.strip()
