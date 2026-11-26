import os

from files.config import DEFAULT_OUTPUT_DIR, resolve_output_dir


def test_default_output_dir_when_unset():
    assert resolve_output_dir({}) == DEFAULT_OUTPUT_DIR
    assert DEFAULT_OUTPUT_DIR.endswith(os.path.join('.smith', 'output'))


def test_blank_value_falls_back_to_default():
    assert resolve_output_dir({'SMITH_OUTPUT_DIR': '  '}) == DEFAULT_OUTPUT_DIR


def test_custom_dir_is_used():
    assert resolve_output_dir({'SMITH_OUTPUT_DIR': '/tmp/pdfs'}) == '/tmp/pdfs'


def test_tilde_is_expanded():
    assert resolve_output_dir({'SMITH_OUTPUT_DIR': '~/Documents/smith'}) == \
        os.path.join(os.path.expanduser('~'), 'Documents', 'smith')
