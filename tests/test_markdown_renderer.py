from app.ui.markdown_renderer import markdown_to_html, markdown_to_plain_text


def test_markdown_to_html_renders_fenced_code_blocks() -> None:
    html = markdown_to_html("```sql\nSELECT * FROM table_name\n```")

    assert "<pre>" in html
    assert "<code" in html
    assert "SELECT * FROM table_name" in html


def test_markdown_to_plain_text_removes_common_markdown_markers() -> None:
    text = markdown_to_plain_text("**Spark SQL** usa `SELECT` e [docs](https://example.com).")

    assert text == "Spark SQL usa SELECT e docs."
