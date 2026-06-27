from app.ui.markdown_renderer import markdown_to_html, markdown_to_plain_text


def test_markdown_to_html_renders_fenced_code_blocks() -> None:
    html = markdown_to_html("```sql\nSELECT * FROM table_name\n```")

    assert "<pre>" in html
    assert "<code" in html
    assert "SELECT * FROM table_name" in html


def test_markdown_to_plain_text_removes_common_markdown_markers() -> None:
    text = markdown_to_plain_text("**Spark SQL** usa `SELECT` e [docs](https://example.com).")

    assert text == "Spark SQL usa SELECT e docs."


def test_markdown_renders_math_subscripts() -> None:
    cases = [
        ("$Q_{retirada}$", "Q<sub>retirada</sub>"),
        ("$Q_{\\retirada}$", "Q<sub>retirada</sub>"),
        ("$Q_{\\text{retirada}}$", "Q<sub>retirada</sub>"),
        ("$Q_{mlt}$", "Q<sub>mlt</sub>"),
        ("$Q_{\\mlt}$", "Q<sub>mlt</sub>"),
        ("SQ_{retirada}", "SQ<sub>retirada</sub>"),
        ("$Q_{<script>}$", "Q<sub>&lt;script&gt;</sub>"),
    ]
    for math_input, expected in cases:
        html_out = markdown_to_html(math_input)
        assert expected in html_out


def test_markdown_protects_code_blocks_from_math_normalization() -> None:
    # Inline code
    html_out = markdown_to_html("`$Q_{retirada}$`")
    assert "Q<sub>" not in html_out
    assert "$Q_{retirada}$" in html_out

    # Fenced code
    fenced = "```\n$Q_{retirada}$\n```"
    html_fenced = markdown_to_html(fenced)
    assert "Q<sub>" not in html_fenced
    assert "$Q_{retirada}$" in html_fenced
