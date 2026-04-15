from datetime import datetime, timezone
from types import SimpleNamespace

from app import streamlit_app
from app.pages import main_page
from modules.domain.models import AnswerAttempt, AnswerEvaluation, DisplayAlternative, Question, QuestionAlternative, User
from modules.services.question_service import SubjectTopicGroup


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


def test_use_topic_only_filter_is_enabled_for_single_subject_group() -> None:
    assert (
        main_page._use_topic_only_filter(
            [SubjectTopicGroup(subject="databricks", topics=("structured streaming",))]
        )
        is True
    )
    assert (
        main_page._use_topic_only_filter(
            [
                SubjectTopicGroup(subject="databricks", topics=("structured streaming",)),
                SubjectTopicGroup(subject="matematica", topics=("divisao",)),
            ]
        )
        is False
    )


def test_ensure_sidebar_subject_topic_filter_widget_state_initializes_from_applied_filters(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={})

    monkeypatch.setattr(main_page, "st", fake_st)

    main_page._ensure_sidebar_subject_topic_filter_widget_state(
        subject_topic_groups=[
            SubjectTopicGroup(subject="databricks", topics=("ingestion", "governance")),
            SubjectTopicGroup(subject="matematica", topics=("divisao",)),
        ],
        selected_subjects=("databricks",),
        selected_topics=(),
    )

    assert fake_st.session_state[main_page._select_all_filters_checkbox_key()] is False
    assert fake_st.session_state[main_page._subject_checkbox_key("databricks")] is True
    assert fake_st.session_state[main_page._subject_checkbox_key("matematica")] is False


def test_ensure_sidebar_subject_topic_filter_widget_state_preserves_unapplied_draft(monkeypatch) -> None:
    subject_topic_groups = [
        SubjectTopicGroup(subject="databricks", topics=("ingestion", "governance")),
        SubjectTopicGroup(subject="matematica", topics=("divisao",)),
    ]
    fake_st = SimpleNamespace(
        session_state={
            main_page._sidebar_filter_widget_scope_key(): main_page._subject_topic_group_specs(subject_topic_groups),
            main_page._sidebar_filter_widget_applied_signature_key(): main_page._filter_selection_signature(
                selected_subjects=("databricks",),
                selected_topics=(),
            ),
            main_page._select_all_filters_checkbox_key(): False,
            main_page._subject_checkbox_key("databricks"): False,
            main_page._subject_checkbox_key("matematica"): False,
            main_page._topic_checkbox_key("databricks", "ingestion"): False,
            main_page._topic_checkbox_key("databricks", "governance"): False,
            main_page._topic_checkbox_key("matematica", "divisao"): False,
        }
    )

    monkeypatch.setattr(main_page, "st", fake_st)

    main_page._ensure_sidebar_subject_topic_filter_widget_state(
        subject_topic_groups=subject_topic_groups,
        selected_subjects=("databricks",),
        selected_topics=(),
    )

    assert fake_st.session_state[main_page._subject_checkbox_key("databricks")] is False


def test_toggle_all_sidebar_subject_topic_filter_widgets_updates_local_widget_state(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={main_page._select_all_filters_checkbox_key(): True})

    monkeypatch.setattr(main_page, "st", fake_st)

    main_page._toggle_all_sidebar_subject_topic_filter_widgets(
        (
            ("databricks", ("ingestion", "governance")),
            ("matematica", ("divisao",)),
        )
    )

    assert fake_st.session_state[main_page._subject_checkbox_key("databricks")] is True
    assert fake_st.session_state[main_page._topic_checkbox_key("databricks", "ingestion")] is True
    assert fake_st.session_state[main_page._topic_checkbox_key("matematica", "divisao")] is True


def test_read_sidebar_subject_topic_filter_widget_state_returns_pending_selection(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            main_page._subject_checkbox_key("databricks"): True,
            main_page._subject_checkbox_key("matematica"): False,
            main_page._topic_checkbox_key("databricks", "ingestion"): True,
            main_page._topic_checkbox_key("databricks", "governance"): False,
            main_page._topic_checkbox_key("matematica", "divisao"): True,
        }
    )

    monkeypatch.setattr(main_page, "st", fake_st)

    selected_subjects, selected_topics = main_page._read_sidebar_subject_topic_filter_widget_state(
        [
            SubjectTopicGroup(subject="databricks", topics=("ingestion", "governance")),
            SubjectTopicGroup(subject="matematica", topics=("divisao",)),
        ]
    )

    assert selected_subjects == ("databricks",)
    assert selected_topics == (("matematica", "divisao"),)


def test_render_sidebar_subject_topic_filters_applies_draft_only_on_apply_click(monkeypatch) -> None:
    applied: dict[str, object] = {}

    class FakeSidebar:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_st = SimpleNamespace(
        session_state={},
        sidebar=FakeSidebar(),
        divider=lambda: None,
        caption=lambda *args, **kwargs: None,
        checkbox=lambda *args, **kwargs: False,
        button=lambda *args, **kwargs: kwargs.get("key") == "gm_sidebar_apply_subject_topic_filters",
        container=lambda: FakeSidebar(),
        html=lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(main_page, "st", fake_st)
    monkeypatch.setattr(
        main_page,
        "_ensure_sidebar_subject_topic_filter_widget_state",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        main_page,
        "_refresh_select_all_filters_checkbox_state",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        main_page,
        "_all_filter_widgets_checked",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        main_page,
        "_read_sidebar_subject_topic_filter_widget_state",
        lambda *args, **kwargs: (("matematica",), ()),
    )
    monkeypatch.setattr(
        main_page,
        "_apply_subject_topic_filters",
        lambda *, subjects, topics: applied.update({"subjects": subjects, "topics": topics}),
    )

    main_page._render_sidebar_subject_topic_filters(
        subject_topic_groups=[SubjectTopicGroup(subject="matematica", topics=("divisao",))],
        selected_subjects=(),
        selected_topics=(),
        selected_filter_label="Tudo",
    )

    assert applied == {
        "subjects": ("matematica",),
        "topics": (),
    }


def test_render_sidebar_subject_topic_filters_renders_spacing_hooks(monkeypatch) -> None:
    rendered_html: list[str] = []

    class FakeSidebar:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_st = SimpleNamespace(
        session_state={},
        sidebar=FakeSidebar(),
        divider=lambda: None,
        caption=lambda *args, **kwargs: None,
        checkbox=lambda *args, **kwargs: False,
        button=lambda *args, **kwargs: False,
        container=lambda: FakeSidebar(),
        html=lambda html: rendered_html.append(html),
    )

    monkeypatch.setattr(main_page, "st", fake_st)
    monkeypatch.setattr(
        main_page,
        "_ensure_sidebar_subject_topic_filter_widget_state",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        main_page,
        "_refresh_select_all_filters_checkbox_state",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        main_page,
        "_all_filter_widgets_checked",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        main_page,
        "_read_sidebar_subject_topic_filter_widget_state",
        lambda *args, **kwargs: ((), ()),
    )

    main_page._render_sidebar_subject_topic_filters(
        subject_topic_groups=[SubjectTopicGroup(subject="matematica", topics=("divisao",))],
        selected_subjects=(),
        selected_topics=(),
        selected_filter_label="Tudo",
    )

    assert any("gm-sidebar-subject-topic-filters-hook" in html for html in rendered_html)
    assert any("gm-sidebar-apply-filters-hook" in html for html in rendered_html)


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


def test_resolve_current_question_prefetches_batch_and_reuses_session_pool(monkeypatch) -> None:
    question_one = Question(
        id_question=7,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4", "Porque 2 + 2 = 4."),
        wrong_answers=(QuestionAlternative("3", "Soma incompleta."),),
        subject="Matematica",
    )
    question_two = Question(
        id_question=8,
        statement="Quanto e 3 + 3?",
        correct_answer=QuestionAlternative("6", "Porque 3 + 3 = 6."),
        wrong_answers=(QuestionAlternative("5", "Faltou 1."),),
        subject="Matematica",
    )
    state = {
        "current_question_id": None,
        "current_question": None,
        "current_alternatives": [],
        "pool": [],
        "pool_scope": None,
        "invalid_ids": set(),
    }
    batch_calls: list[tuple[int, ...]] = []

    def _set_current_question(question, alternatives):
        state["current_question_id"] = question.id_question
        state["current_question"] = question
        state["current_alternatives"] = alternatives

    monkeypatch.setattr(streamlit_app, "get_current_question_id", lambda: state["current_question_id"])
    monkeypatch.setattr(streamlit_app, "get_current_question", lambda: state["current_question"])
    monkeypatch.setattr(streamlit_app, "get_current_alternatives", lambda: state["current_alternatives"])
    monkeypatch.setattr(
        streamlit_app,
        "clear_current_question",
        lambda: state.update({"current_question_id": None, "current_question": None, "current_alternatives": []}),
    )
    monkeypatch.setattr(streamlit_app, "get_skipped_question_ids", lambda: set())
    monkeypatch.setattr(streamlit_app, "get_invalid_question_ids", lambda: set(state["invalid_ids"]))
    monkeypatch.setattr(streamlit_app, "mark_question_invalid", lambda id_question: state["invalid_ids"].add(id_question))
    monkeypatch.setattr(streamlit_app, "get_question_pool", lambda: list(state["pool"]))
    monkeypatch.setattr(
        streamlit_app,
        "ensure_question_pool_scope",
        lambda scope_key: state.update({"pool_scope": scope_key, "pool": []})
        if state["pool_scope"] != scope_key
        else None,
    )
    monkeypatch.setattr(
        streamlit_app,
        "set_question_pool",
        lambda questions, scope_key=None: state.update(
            {
                "pool": list(questions),
                "pool_scope": scope_key if scope_key is not None else state["pool_scope"],
            }
        ),
    )
    monkeypatch.setattr(streamlit_app, "set_current_question", _set_current_question)
    monkeypatch.setattr(
        streamlit_app,
        "build_display_alternatives",
        lambda question: [
            DisplayAlternative(
                option_id=f"option_{question.id_question}",
                alternative_text=question.correct_answer.alternative_text,
                explanation=question.correct_answer.explanation,
                is_correct=True,
            )
        ],
    )
    monkeypatch.setattr(streamlit_app, "select_question_batch_ids", lambda *args, **kwargs: [7, 8])
    monkeypatch.setattr(
        streamlit_app,
        "load_question_batch",
        lambda *args, **kwargs: (batch_calls.append(tuple(kwargs.get("question_ids", args[2]))) or [question_one, question_two], []),
    )
    monkeypatch.setattr(
        streamlit_app,
        "load_question_snapshot",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("single-question lookup should not run")),
    )

    resolved_question, resolved_alternatives, issues = streamlit_app.resolve_current_question(
        question_repository=SimpleNamespace(),
        question_table_id="project.dataset.question_bank",
        cohort_key="ano_1",
        active_question_ids=[7, 8],
        answered_question_ids=set(),
    )

    assert resolved_question == question_one
    assert [question.id_question for question in state["pool"]] == [8]
    assert resolved_alternatives[0].option_id == "option_7"
    assert issues == []
    assert batch_calls == [(7, 8)]

    state["current_question_id"] = None
    state["current_question"] = None
    state["current_alternatives"] = []

    resolved_question, resolved_alternatives, issues = streamlit_app.resolve_current_question(
        question_repository=SimpleNamespace(),
        question_table_id="project.dataset.question_bank",
        cohort_key="ano_1",
        active_question_ids=[7, 8],
        answered_question_ids=set(),
    )

    assert resolved_question == question_two
    assert state["pool"] == []
    assert resolved_alternatives[0].option_id == "option_8"
    assert issues == []
    assert batch_calls == [(7, 8)]


def test_resolve_authorized_user_reuses_cached_session_user(monkeypatch) -> None:
    cached_user = User(email="ana@example.com", name="Ana", role="teacher", cohort_key="all")
    bind_calls: list[User] = []

    monkeypatch.setattr(streamlit_app, "get_authenticated_user", lambda: cached_user)
    monkeypatch.setattr(streamlit_app, "bind_authenticated_user", lambda user: bind_calls.append(user))

    resolved_user = streamlit_app._resolve_authorized_user(
        authorization_service=SimpleNamespace(
            authorize=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not reauthorize"))
        ),
        email=" ANA@example.com ",
        fallback_name="Ana OAuth",
    )

    assert resolved_user == cached_user
    assert bind_calls == [cached_user]


def test_ensure_leaderboard_position_loaded_reuses_session_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(streamlit_app, "has_loaded_leaderboard_position", lambda user_email: True)
    monkeypatch.setattr(
        streamlit_app,
        "get_leaderboard_position",
        lambda user_email: (2, 9, ["cached issue"]),
    )

    leaderboard = streamlit_app._ensure_leaderboard_position_loaded(
        answer_repository=SimpleNamespace(),
        answers_table_id="project.dataset.answers",
        user_access_table_id="project.dataset.user_access",
        user_email="ana@example.com",
        role="teacher",
        cohort_key=None,
    )

    assert leaderboard == (2, 9, ["cached issue"])


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


def test_build_question_card_html_renders_markdown_snippets() -> None:
    html = main_page._build_question_card_html("```sql\nSELECT 1\n```")

    assert "<pre>" in html
    assert "SELECT 1" in html


def test_build_pending_alternative_card_html_renders_markdown_and_selected_state() -> None:
    html = main_page._build_pending_alternative_card_html(
        alternative=DisplayAlternative(
            option_id="option_sql",
            alternative_text="```python\nprint('ok')\n```",
            explanation=None,
            is_correct=False,
        ),
        is_selected=True,
    )

    assert "gm-live-pending-choice-card--selected" in html
    assert "<pre>" in html
    assert "print('ok')" in html


def test_apply_live_page_styles_tunes_pending_choice_gap_and_padding(monkeypatch) -> None:
    rendered_html: list[str] = []

    monkeypatch.setattr(main_page.st, "html", lambda html: rendered_html.append(html))

    main_page._apply_live_page_styles()

    assert len(rendered_html) == 1
    stylesheet = rendered_html[0]
    assert "--gm-topbar-alignment-offset: 0.18rem;" in stylesheet
    assert "--gm-pending-choice-gap: 0.48rem;" in stylesheet
    assert "--gm-pending-choice-label-gap: 0.3rem;" in stylesheet
    assert "--gm-pending-choice-padding-block: 0.56rem;" in stylesheet
    assert "--gm-pending-choice-padding-inline: 0.62rem;" in stylesheet
    assert "margin: 0.18rem 0 var(--gm-pending-choice-label-gap);" in stylesheet
    assert "gap: var(--gm-pending-choice-gap) !important;" in stylesheet
    assert "column-gap: var(--gm-pending-choice-gap) !important;" in stylesheet
    assert "min-height: calc(2.55rem + var(--gm-topbar-alignment-offset));" in stylesheet
    assert "padding-top: var(--gm-topbar-alignment-offset);" in stylesheet
    assert "padding: var(--gm-pending-choice-padding-block) var(--gm-pending-choice-padding-inline) !important;" in stylesheet


def test_apply_live_page_styles_keeps_native_sidebar_toggle_unstyled(monkeypatch) -> None:
    rendered_html: list[str] = []

    monkeypatch.setattr(main_page.st, "html", lambda html: rendered_html.append(html))

    main_page._apply_live_page_styles()

    assert len(rendered_html) == 1
    stylesheet = rendered_html[0]
    assert "border-right: 1px solid #dbeafe !important;" in stylesheet
    assert '[data-testid="stHeader"]' not in stylesheet
    assert 'button[kind="header"][aria-label*="sidebar" i]' not in stylesheet
    assert 'section[data-testid="stSidebar"][aria-expanded="false"]' not in stylesheet


def test_apply_live_page_styles_tunes_sidebar_filter_spacing_and_primary_button_text(monkeypatch) -> None:
    rendered_html: list[str] = []

    monkeypatch.setattr(main_page.st, "html", lambda html: rendered_html.append(html))

    main_page._apply_live_page_styles()

    assert len(rendered_html) == 1
    stylesheet = rendered_html[0]
    assert "gm-sidebar-subject-topic-filters-hook" in stylesheet
    assert "gap: 0.38rem !important;" in stylesheet
    assert "padding-top: 0.48rem !important;" in stylesheet
    assert 'button[kind="primary"] {' in stylesheet
    assert "color: #ffffff !important;" in stylesheet


def test_format_pending_widget_label_unwraps_fenced_code_blocks() -> None:
    label = main_page._format_pending_widget_label(
        "```sql\nSELECT *\nFROM bronze.orders\n```"
    )

    assert label == "SELECT *\nFROM bronze.orders"


def test_format_pending_widget_label_preserves_inline_markdown_when_possible() -> None:
    label = main_page._format_pending_widget_label(
        "Use `Type 1` and compare with `Type 2`."
    )

    assert label == "Use `Type 1` and compare with `Type 2`."


def test_format_rank_text_preserves_rank_and_total_users() -> None:
    assert main_page._format_rank_text("#1 / 10") == "#1/10"
    assert main_page._format_rank_text("#3/12") == "#3/12"
    assert main_page._format_rank_text("") == "#-"


def test_build_answer_status_chip_html_matches_result_state() -> None:
    correct_html = main_page._build_answer_status_chip_html(True)
    wrong_html = main_page._build_answer_status_chip_html(False)

    assert "Você acertou" in correct_html
    assert "gm-live-status-chip--correct" in correct_html
    assert "Você errou" in wrong_html
    assert "gm-live-status-chip--wrong" in wrong_html


def test_build_metrics_bar_html_orders_day_and_question_streak_icons() -> None:
    html = main_page._build_metrics_bar_html(
        day_streak_text="5",
        question_streak_text="3",
        rank_text="#1",
        timer_text="00:12",
        timer_warning=False,
        calendar_icon_data_uri="calendar-uri",
        fire_icon_data_uri="fire-uri",
        podium_icon_data_uri="podium-uri",
        timer_icon_data_uri="timer-uri",
    )

    assert html.index("calendar-uri") < html.index("fire-uri")
    assert html.index("fire-uri") < html.index("podium-uri")
    assert ">5<" in html
    assert ">3<" in html
    assert "Dias seguidos com atividade." in html
    assert "Sequência atual de respostas corretas." in html


def test_streak_text_helpers_use_day_and_question_values_independently() -> None:
    assert main_page._format_day_streak_text(4) == "4"
    assert main_page._format_day_streak_text(-1) == "0"
    assert main_page._format_question_streak_text(7) == "7"
    assert main_page._format_question_streak_text(-2) == "0"


def test_resolve_live_timer_text_uses_current_time_when_running(monkeypatch) -> None:
    monkeypatch.setattr(
        main_page,
        "utc_now",
        lambda: datetime(2026, 4, 8, 16, 0, 9, tzinfo=timezone.utc),
    )

    timer_text = main_page._resolve_live_timer_text(
        timer_elapsed_seconds=0,
        timer_started_at=datetime(2026, 4, 8, 16, 0, 0, tzinfo=timezone.utc),
    )

    assert timer_text == "00:09"


def test_resolve_live_timer_text_falls_back_to_existing_elapsed_seconds() -> None:
    timer_text = main_page._resolve_live_timer_text(
        timer_elapsed_seconds=112,
        timer_started_at=None,
    )

    assert timer_text == "01:52"


def test_resolve_live_timer_seconds_uses_current_time_when_running(monkeypatch) -> None:
    monkeypatch.setattr(
        main_page,
        "utc_now",
        lambda: datetime(2026, 4, 8, 16, 2, 5, tzinfo=timezone.utc),
    )

    elapsed_seconds = main_page._resolve_live_timer_seconds(
        timer_elapsed_seconds=40,
        timer_started_at=datetime(2026, 4, 8, 16, 0, 0, tzinfo=timezone.utc),
    )

    assert elapsed_seconds == 125
    assert main_page._is_timer_warning(elapsed_seconds) is True


def test_build_metric_chip_html_marks_timer_as_warning_after_threshold() -> None:
    html = main_page._build_metric_chip_html(
        "02:00",
        "",
        description="Tempo gasto na questão atual.",
        is_timer=True,
        timer_warning=True,
    )

    assert "gm-live-metric--timer-warning" in html
    assert "gm-live-metric-tooltip" in html
