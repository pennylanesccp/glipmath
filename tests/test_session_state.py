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


def test_question_pool_round_trips_through_session_state(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    question_one = Question(
        id_question=11,
        statement="Quanto e 5 + 5?",
        correct_answer=QuestionAlternative("10"),
        wrong_answers=(QuestionAlternative("9"),),
    )
    question_two = Question(
        id_question=12,
        statement="Quanto e 6 + 6?",
        correct_answer=QuestionAlternative("12"),
        wrong_answers=(QuestionAlternative("11"),),
    )

    session_state.set_question_pool([question_one, question_two], scope_key="ano_1|matematica")

    assert session_state.get_question_pool() == [question_one, question_two]
    assert session_state.get_question_pool_scope() == "ano_1|matematica"


def test_ensure_question_pool_scope_resets_pool_when_scope_changes(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    question = Question(
        id_question=11,
        statement="Quanto e 5 + 5?",
        correct_answer=QuestionAlternative("10"),
        wrong_answers=(QuestionAlternative("9"),),
    )

    session_state.set_question_pool([question], scope_key="ano_1|matematica")
    session_state.ensure_question_pool_scope("ano_2|matematica")

    assert session_state.get_question_pool() == []
    assert session_state.get_question_pool_scope() == "ano_2|matematica"


def test_bind_authenticated_user_resets_when_scope_changes(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    first_user = User(email="ana@example.com", role="student", cohort_key="ano_1")
    second_user = User(email="ana@example.com", role="student", cohort_key="ano_2")

    session_state.bind_authenticated_user(first_user)
    session_state.set_subject_filters(("Matematica",))
    session_state.set_topic_filters((("Portugues", "gramatica"),))
    session_state.set_project_filter("crescer_e_conectar")
    session_state.set_question_pool(
        [
            Question(
                id_question=11,
                statement="Quanto e 5 + 5?",
                correct_answer=QuestionAlternative("10"),
                wrong_answers=(QuestionAlternative("9"),),
            )
        ],
        scope_key="ano_1|matematica",
    )

    session_state.bind_authenticated_user(second_user)

    assert session_state.get_subject_filters() == ()
    assert session_state.get_topic_filters() == ()
    assert session_state.get_project_filter() is None
    assert session_state.get_current_question() is None
    assert session_state.get_question_pool() == []


def test_get_authenticated_user_returns_bound_user(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    user = User(email="ana@example.com", name="Ana", role="teacher", cohort_key="all")
    session_state.bind_authenticated_user(user)

    assert session_state.get_authenticated_user() == user


def test_bind_authenticated_user_resets_authenticated_run_log_flag(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    first_user = User(email="ana@example.com", role="student", cohort_key="ano_1")
    second_user = User(email="ana@example.com", role="student", cohort_key="ano_2")

    session_state.bind_authenticated_user(first_user)
    session_state.mark_authenticated_run_logged()

    assert session_state.has_logged_authenticated_run() is True

    session_state.bind_authenticated_user(second_user)

    assert session_state.has_logged_authenticated_run() is False


def test_leaderboard_position_round_trips_through_session_state(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    session_state.set_leaderboard_position(
        "ana@example.com",
        3,
        14,
        issues=["lag temporary"],
    )

    assert session_state.has_loaded_leaderboard_position("ana@example.com") is True
    assert session_state.get_leaderboard_position("ana@example.com") == (3, 14, ["lag temporary"])


def test_professor_notice_round_trips_through_session_state(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    session_state.set_professor_notice("success", "Questão enviada.")

    assert session_state.get_professor_notice() == {
        "kind": "success",
        "message": "Questão enviada.",
    }

    session_state.clear_professor_notice()

    assert session_state.get_professor_notice() is None


def test_professor_authoring_ai_assisted_flag_round_trips(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    session_state.set_professor_authoring_ai_assisted(True)
    assert session_state.get_professor_authoring_ai_assisted() is True

    session_state.set_professor_authoring_ai_assisted(False)
    assert session_state.get_professor_authoring_ai_assisted() is False


def test_multi_subject_topic_filters_round_trip(monkeypatch) -> None:
    monkeypatch.setattr(session_state, "st", SimpleNamespace(session_state={}))

    session_state.set_subject_filters(("Portugues", "Matematica"))
    session_state.set_topic_filters((("Ciencias", "ecologia"), ("Matematica", "divisao")))

    assert session_state.get_subject_filters() == ("Matematica", "Portugues")
    assert session_state.get_topic_filters() == (
        ("Ciencias", "ecologia"),
        ("Matematica", "divisao"),
    )
