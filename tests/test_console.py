from cli import console
from cli.prompt import _prompt_style


def test_stats_use_the_prompt_text_color(capsys):
    console.print_stats("Tokens: 1")
    out = capsys.readouterr().out
    assert out.startswith("\033[38;2;170;170;170mTokens: 1")  # #aaaaaa
    assert "\033[0m" in out  # color is reset after the line


def test_prompt_text_color_is_shared_with_the_prompt_style():
    assert console.PROMPT_TEXT_COLOR == "#aaaaaa"
    attrs = _prompt_style.get_attrs_for_style_str("class:normal-text")
    assert attrs.color == "aaaaaa"


def test_ansi_foreground_conversion():
    assert console._ansi_foreground("#ff0066") == "\033[38;2;255;0;102m"
