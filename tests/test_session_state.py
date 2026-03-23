from types import SimpleNamespace

from app.state import session_state
from modules.domain.models import DisplayAlternative, Question, QuestionAlternative, User


def test_current_question_snapshot_round_trips_through_session_state(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    question = Question(
        id_question=11,
        statement="Quanto e 5 + 5?",
        correct_answer=QuestionAlternative("10", "Soma correta."),
        wrong_answers=(
            QuestionAlternative("9", "Faltou 1."),
            QuestionAlternative("11", "Passou 1."),
        ),
        subject="Matematica",
        topic="Aritmetica",
        difficulty="facil",
        source="seed",
    )
    alternatives = [
        DisplayAlternative(
            option_id="option_a",
            alternative_text="10",
            explanation="Soma correta.",
            is_correct=True,
        ),
        DisplayAlternative(
            option_id="option_b",
            alternative_text="9",
            explanation="Faltou 1.",
            is_correct=False,
        ),
    ]

    session_state.set_current_question(question, alternatives)

    assert session_state.get_current_question() == question
    assert session_state.get_current_alternatives() == alternatives


def test_clear_current_question_clears_question_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    question = Question(
        id_question=11,
        statement="Quanto e 5 + 5?",
        correct_answer=QuestionAlternative("10"),
        wrong_answers=(QuestionAlternative("9"),),
    )

    session_state.set_current_question(question, [])
    session_state.clear_current_question()

    assert session_state.get_current_question() is None
    assert session_state.get_current_alternatives() == []


def test_bind_authenticated_user_resets_when_scope_changes(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    first_user = User(email="ana@example.com", role="student", cohort_key="ano_1")
    second_user = User(email="ana@example.com", role="student", cohort_key="ano_2")

    session_state.bind_authenticated_user(first_user)
    session_state.set_subject_filter("Matematica")

    session_state.bind_authenticated_user(second_user)

    assert session_state.get_subject_filter_label() == "Todas"
    assert session_state.get_current_question() is None
