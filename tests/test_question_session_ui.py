from app.ui.question_session import format_elapsed_time, text_to_html


def test_format_elapsed_time_formats_minutes_and_seconds() -> None:
    assert format_elapsed_time(0) == "00:00"
    assert format_elapsed_time(65.9) == "01:05"


def test_format_elapsed_time_formats_hours_when_needed() -> None:
    assert format_elapsed_time(3723) == "1:02:03"


def test_text_to_html_renders_markdown_code_blocks() -> None:
    html = text_to_html("```python\nprint('oi')\n```")

    assert "<pre>" in html
    assert "print('oi')" in html
