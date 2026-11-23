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


def test_empty_model_path_has_clear_message():
    with pytest.raises(ValueError, match="LLAMA_MODEL_PATH is not set"):
        LlamaConfig(model_name="m", llama_model_path="")


def test_numeric_fields_are_coerced_from_strings(tmp_path):
    path = tmp_path / "m.gguf"
    path.write_text("x")
    config = LlamaConfig(model_name="m", llama_model_path=str(path),
                         llama_gpu_layers="3", llama_context_size="4096")
    assert (config.llama_gpu_layers, config.llama_context_size) == (3, 4096)


def test_non_numeric_gpu_layers_is_a_validation_error(tmp_path):
    path = tmp_path / "m.gguf"
    path.write_text("x")
    with pytest.raises(ValueError, match="llama_gpu_layers"):
        LlamaConfig(model_name="m", llama_model_path=str(path), llama_gpu_layers="abc")
