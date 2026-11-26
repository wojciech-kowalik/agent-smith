import pytest
from fpdf import FPDF

from commands.session_to_pdf import export_session_to_pdf
from files.pdf import pdf as pdf_module

ANSWER = """Zażółć gęślą jaźń, **bold**.

```python
def f(x):
    return x < 3
```

| a | b |
|---|---|
| 1 | 2 |
"""


@pytest.fixture
def exported(tmp_path, monkeypatch):
    """Exports a session to tmp_path and returns (pdf path, the HTML handed to the PDF writer)."""
    monkeypatch.setattr(pdf_module, "OUTPUT_DIR", str(tmp_path))
    captured = []
    original = FPDF.write_html

    def spy(self, html, *args, **kwargs):
        captured.append(html)
        return original(self, html, *args, **kwargs)

    monkeypatch.setattr(FPDF, "write_html", spy)
    history = [
        {"role": "user", "parts": [{"text": "Napisz kod"}]},
        {"role": "model", "parts": [{"text": ANSWER}]},
    ]
    export_session_to_pdf(history, "abc", "Smith")
    return tmp_path / "abc.pdf", captured[0]


def test_creates_a_pdf_file(exported):
    path, _ = exported
    assert path.read_bytes().startswith(b"%PDF")


def test_fenced_code_block_keeps_its_lines(exported):
    _, html = exported
    assert "<pre><code" in html
    assert "def f(x):\n    return x &lt; 3" in html


def test_markdown_table_becomes_html_table(exported):
    _, html = exported
    assert "<table>" in html and "<th>a</th>" in html and "<td>2</td>" in html


def test_polish_characters_and_headings_survive(exported):
    _, html = exported
    assert "Zażółć gęślą jaźń" in html
    assert "<h1>Chat Session: abc</h1>" in html
    assert "<h2>Smith</h2>" in html


def test_empty_history_creates_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_module, "OUTPUT_DIR", str(tmp_path))
    export_session_to_pdf([], "abc", "Smith")
    assert list(tmp_path.iterdir()) == []
