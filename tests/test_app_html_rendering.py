from types import SimpleNamespace

from app.pages import login_page, main_page
from modules.domain.models import DisplayAlternative, Question, QuestionAlternative, User


def test_render_login_page_uses_streamlit_html(monkeypatch) -> None:
    html_calls: list[str] = []

    monkeypatch.setattr(login_page, "_consume_login_actions", lambda settings: None)
    monkeypatch.setattr(login_page, "asset_to_data_uri", lambda relative_path: "data:image/png;base64,abc")
    monkeypatch.setattr(login_page, "render_template", lambda template_path, context: "<section>login</section>")
    monkeypatch.setattr(login_page.st, "html", lambda html: html_calls.append(html))
    monkeypatch.setattr(
        login_page.st,
        "markdown",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("st.markdown should not be used here")),
    )

    settings = SimpleNamespace(auth=SimpleNamespace(is_configured=True))

    login_page.render_login_page(settings)

    assert html_calls == ["<section>login</section>"]


def test_render_main_page_uses_streamlit_html(monkeypatch) -> None:
    html_calls: list[str] = []

    monkeypatch.setattr(main_page, "initialize_session_state", lambda: None)
    monkeypatch.setattr(main_page, "_consume_page_actions", lambda **kwargs: None)
    monkeypatch.setattr(main_page, "is_current_question_answered", lambda: False)
    monkeypatch.setattr(main_page, "get_last_answer_result", lambda: None)
    monkeypatch.setattr(main_page, "_selected_option_id_for_render", lambda current_question_id: None)
    monkeypatch.setattr(main_page, "_resolve_elapsed_seconds", lambda **kwargs: 12)
    monkeypatch.setattr(
        main_page,
        "render_question_session_template",
        lambda **kwargs: "<section>question</section>",
    )
    monkeypatch.setattr(main_page.st, "html", lambda html: html_calls.append(html))
    monkeypatch.setattr(
        main_page.st,
        "markdown",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("st.markdown should not be used here")),
    )

    question = Question(
        id_question=7,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4"),
        wrong_answers=(QuestionAlternative("3"),),
        subject="Matematica",
    )

    main_page.render_main_page(
        user=User(email="ana@example.com", name="Ana"),
        current_question=question,
        alternatives=[
            DisplayAlternative(
                option_id="option_a",
                alternative_text="4",
                explanation=None,
                is_correct=True,
            )
        ],
        answer_service=object(),
        subject_options=["Todas", "Matematica"],
        selected_subject="Matematica",
        day_streak=3,
        question_streak=5,
        leaderboard_position="#2 / 10",
    )

    assert html_calls == ["<section>question</section>"]
