import pytest
from pydantic import ValidationError

from llm.llama import create_llama_client
from llm.llama_validation import LlamaConfig


def test_missing_model_path_is_rejected():
    with pytest.raises(ValidationError):
        create_llama_client()


def test_model_file_must_exist(tmp_path):
    with pytest.raises(ValidationError, match="does not exist"):
        LlamaConfig(model_name="m", llama_model_path=str(tmp_path / "missing.gguf"))


def test_model_file_needs_gguf_extension(tmp_path):
    path = tmp_path / "model.bin"
    path.write_bytes(b"x")
    with pytest.raises(ValidationError, match=".gguf"):
        LlamaConfig(model_name="m", llama_model_path=str(path))


def test_valid_config(tmp_path):
    path = tmp_path / "model.gguf"
    path.write_bytes(b"x")
    config = LlamaConfig(model_name="m", llama_model_path=str(path))
    assert (config.llama_gpu_layers, config.llama_context_size) == (1, 2048)
