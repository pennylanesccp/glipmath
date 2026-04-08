from datetime import datetime, timezone
from types import SimpleNamespace

from app import streamlit_app
from app.pages import main_page
from modules.domain.models import AnswerAttempt, AnswerEvaluation, DisplayAlternative, Question, QuestionAlternative, User


def test_submit_selected_answer_marks_question_answered(monkeypatch) -> None:
    calls: list[object] = []
    question = Question(
        id_question=7,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4", "Porque 2 + 2 = 4."),
        wrong_answers=(QuestionAlternative("3", "Soma incompleta."),),
        subject="Matematica",
    )
    alternatives = [
        DisplayAlternative(
            option_id="option_a",
            alternative_text="4",
            explanation="Porque 2 + 2 = 4.",
            is_correct=True,
        ),
        DisplayAlternative(
            option_id="option_b",
            alternative_text="3",
            explanation="Soma incompleta.",
            is_correct=False,
        ),
    ]
    evaluation = AnswerEvaluation(
        record=AnswerAttempt(
            id_answer="a1",
            id_question=7,
            user_email="ana@example.com",
            selected_alternative_text="4",
            correct_alternative_text="4",
            is_correct=True,
            answered_at_utc=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 23, 9, 0),
            time_spent_seconds=9.0,
            session_id="session-1",
            subject="Matematica",
        ),
        feedback_message="Resposta correta.",
        correct_explanation="Porque 2 + 2 = 4.",
    )
    answer_service = SimpleNamespace(submit_answer=lambda **kwargs: evaluation)

    monkeypatch.setattr(main_page, "start_submission", lambda: calls.append("start"))
    monkeypatch.setattr(main_page, "get_question_started_at", lambda: datetime(2026, 3, 23, 11, 59, 51, tzinfo=timezone.utc))
    monkeypatch.setattr(main_page, "utc_now", lambda: datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(main_page, "append_user_answer_attempt", lambda email, answer: calls.append(("append", email, answer.id_question)))
    monkeypatch.setattr(main_page, "clear_question_skip", lambda id_question: calls.append(("clear_skip", id_question)))
    monkeypatch.setattr(
        main_page,
        "mark_question_answered",
        lambda evaluation, selected_option_id: calls.append(("mark_answered", evaluation.record.id_question, selected_option_id)),
    )
    monkeypatch.setattr(main_page.st, "rerun", lambda: calls.append("rerun"))

    main_page._submit_selected_answer(
        user=User(email="ana@example.com", name="Ana"),
        current_question=question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id="option_a",
    )

    assert "start" in calls
    assert ("append", "ana@example.com", 7) in calls
    assert ("clear_skip", 7) in calls
    assert ("mark_answered", 7, "option_a") in calls
    assert "rerun" in calls


def test_submit_selected_answer_rejects_missing_option(monkeypatch) -> None:
    warnings: list[str] = []
    question = Question(
        id_question=7,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4"),
        wrong_answers=(QuestionAlternative("3"),),
    )
    alternatives = [
        DisplayAlternative(
            option_id="option_a",
            alternative_text="4",
            explanation=None,
            is_correct=True,
        )
    ]

    monkeypatch.setattr(main_page.st, "warning", lambda message: warnings.append(str(message)))

    main_page._submit_selected_answer(
        user=User(email="ana@example.com", name="Ana"),
        current_question=question,
        alternatives=alternatives,
        answer_service=SimpleNamespace(submit_answer=lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not submit"))),
        selected_option_id="option_b",
    )

    assert warnings == ["Seleção inválida para a questão atual."]


def test_resolve_current_question_reuses_loaded_snapshot(monkeypatch) -> None:
    question = Question(
        id_question=7,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4", "Porque 2 + 2 = 4."),
        wrong_answers=(QuestionAlternative("3", "Soma incompleta."),),
        subject="Matematica",
    )
    alternatives = [
        DisplayAlternative(
            option_id="option_a",
            alternative_text="4",
            explanation="Porque 2 + 2 = 4.",
            is_correct=True,
        )
    ]

    monkeypatch.setattr(streamlit_app, "get_current_question_id", lambda: 7)
    monkeypatch.setattr(streamlit_app, "get_current_question", lambda: question)
    monkeypatch.setattr(streamlit_app, "get_current_alternatives", lambda: alternatives)

    resolved_question, resolved_alternatives, issues = streamlit_app.resolve_current_question(
        question_repository=SimpleNamespace(
            load_question_frame_by_id=lambda question_id: (_ for _ in ()).throw(
                AssertionError("question snapshot should not be reloaded")
            )
        ),
        question_table_id="project.dataset.question_bank",
        cohort_key="ano_1",
        active_question_ids=[7],
        answered_question_ids=set(),
    )

    assert resolved_question == question
    assert resolved_alternatives == alternatives
    assert issues == []


def test_build_answer_review_card_html_uses_wrong_style_for_all_incorrect_options() -> None:
    wrong_html = main_page._build_answer_review_card_html(
        alternative=DisplayAlternative(
            option_id="option_b",
            alternative_text="6",
            explanation="Se fossem 6 por prateleira, seriam 24 carrinhos.",
            is_correct=False,
        ),
        selected_option_id="option_a",
    )
    correct_html = main_page._build_answer_review_card_html(
        alternative=DisplayAlternative(
            option_id="option_a",
            alternative_text="4",
            explanation="16 dividido por 4 é igual a 4.",
            is_correct=True,
        ),
        selected_option_id="option_a",
    )

    assert "gm-live-answer-card--wrong" in wrong_html
    assert "gm-live-answer-card--correct" in correct_html
    assert "Sua resposta" in correct_html
    assert "Gabarito" not in correct_html


def test_build_answer_status_chip_html_matches_result_state() -> None:
    correct_html = main_page._build_answer_status_chip_html(True)
    wrong_html = main_page._build_answer_status_chip_html(False)

    assert "Acertou" in correct_html
    assert "gm-live-status-chip--correct" in correct_html
    assert "Errou" in wrong_html
    assert "gm-live-status-chip--wrong" in wrong_html
