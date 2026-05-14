import pandas as pd
from types import SimpleNamespace

from app import streamlit_app
from app.components import sidebar
from app.state.session_state import (
    get_current_professor_tool,
    initialize_session_state,
    set_current_professor_tool,
)
from modules.domain.models import User
from modules.services.question_service import QuestionFilterSelection, SubjectTopicGroup


class FakeQuestionRepository:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.received_cohort_key = "unset"

    def load_active_index_frame(self, *, cohort_key=None) -> pd.DataFrame:
        self.received_cohort_key = cohort_key
        return self.frame

    def load_active_project_frame(self) -> pd.DataFrame:
        return self.frame


def test_load_active_question_index_scopes_students_to_their_cohort() -> None:
    streamlit_app.load_active_question_index.clear()
    repository = FakeQuestionRepository(
        pd.DataFrame(
            [
                {"id_question": 1, "subject": "Matematica", "cohort_key": "ano_1"},
            ]
        )
    )

    question_index, issues = streamlit_app.load_active_question_index(
        repository,
        "project.dataset.question_bank",
        "ano_1",
    )

    assert not issues
    assert repository.received_cohort_key == "ano_1"
    assert [entry.id_question for entry in question_index] == [1]


def test_load_active_question_index_keeps_teacher_scope_global() -> None:
    streamlit_app.load_active_question_index.clear()
    repository = FakeQuestionRepository(
        pd.DataFrame(
            [
                {"id_question": 1, "subject": "Matematica", "cohort_key": "ano_1"},
                {"id_question": 2, "subject": "Matematica", "cohort_key": "ano_2"},
            ]
        )
    )

    question_index, issues = streamlit_app.load_active_question_index(
        repository,
        "project.dataset.question_bank",
        None,
    )

    assert not issues
    assert repository.received_cohort_key is None
    assert [entry.id_question for entry in question_index] == [1, 2]


def test_load_active_project_options_reads_distinct_projects_for_teacher_filter() -> None:
    streamlit_app.load_active_project_options.clear()
    repository = FakeQuestionRepository(
        pd.DataFrame(
            [
                {"cohort_key": "Ano_1"},
                {"cohort_key": "crescer_e_conectar"},
                {"cohort_key": "ano_1"},
            ]
        )
    )

    project_options, issues = streamlit_app.load_active_project_options(
        repository,
        "project.dataset.question_bank",
    )

    assert not issues
    assert project_options == ["ano_1", "crescer_e_conectar"]


def test_resolve_project_options_for_non_global_user_avoids_project_catalog_query() -> None:
    repository = FakeQuestionRepository(pd.DataFrame())
    user = User(
        email="prof@example.com",
        role="teacher",
        cohort_key="crescer_e_conectar",
        accessible_cohort_keys=("crescer_e_conectar", "rumo_etec"),
    )

    project_options, issues = streamlit_app._resolve_project_options_for_user(
        user=user,
        question_repository=repository,
        question_table_id="project.dataset.question_bank",
    )

    assert project_options == ["crescer_e_conectar", "rumo_etec"]
    assert issues == []
    assert repository.received_cohort_key == "unset"


def test_render_authenticated_shell_clears_professor_tool_for_student_only_user(monkeypatch) -> None:
    initialize_session_state()
    set_current_professor_tool("add_student")
    user = User(
        email="aluno@example.com",
        role="student",
        cohort_key="crescer_e_conectar",
        accessible_cohort_keys=("crescer_e_conectar",),
    )

    class FakeSidebar:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_st = SimpleNamespace(
        sidebar=FakeSidebar(),
        session_state={},
        container=lambda: FakeSidebar(),
        html=lambda *args, **kwargs: None,
        caption=lambda *args, **kwargs: None,
        segmented_control=lambda *args, **kwargs: "practice",
        rerun=lambda: (_ for _ in ()).throw(AssertionError("should not rerun")),
    )

    monkeypatch.setattr(sidebar, "st", fake_st)
    monkeypatch.setattr(sidebar, "get_project_filter", lambda: "crescer_e_conectar")
    monkeypatch.setattr(sidebar, "get_current_student_view", lambda: "practice")

    selected_project, current_workspace = sidebar._render_authenticated_shell_sidebar(
        user=user,
        project_options=["crescer_e_conectar"],
        selected_project="crescer_e_conectar",
    )

    assert selected_project == "crescer_e_conectar"
    assert current_workspace == "student"
    assert get_current_professor_tool() is None


def test_render_authenticated_shell_sidebar_reads_current_sidebar_choices_without_rerun(monkeypatch) -> None:
    initialize_session_state()
    user = User(
        email="prof@example.com",
        role="teacher",
        cohort_key="crescer_e_conectar",
        accessible_cohort_keys=("crescer_e_conectar", "rumo_etec"),
    )

    class FakeSidebar:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_st = SimpleNamespace(
        sidebar=FakeSidebar(),
        session_state={},
        container=lambda: FakeSidebar(),
        html=lambda *args, **kwargs: None,
        caption=lambda *args, **kwargs: None,
        selectbox=lambda *args, **kwargs: "rumo_etec",
        columns=lambda *args, **kwargs: (FakeSidebar(), FakeSidebar()),
        button=lambda *args, **kwargs: False,
        segmented_control=lambda *args, **kwargs: "stats",
        rerun=lambda: (_ for _ in ()).throw(AssertionError("should not rerun")),
    )

    monkeypatch.setattr(sidebar, "st", fake_st)
    monkeypatch.setattr(sidebar, "get_project_filter", lambda: "rumo_etec")
    monkeypatch.setattr(sidebar, "get_current_workspace", lambda: "student")
    monkeypatch.setattr(sidebar, "get_current_student_view", lambda: "stats")

    selected_project, current_workspace = sidebar._render_authenticated_shell_sidebar(
        user=user,
        project_options=["crescer_e_conectar", "rumo_etec"],
        selected_project="rumo_etec",
    )

    assert selected_project == "rumo_etec"
    assert current_workspace == "student"


def test_render_sidebar_ui_applies_styles_before_controls(monkeypatch) -> None:
    calls: list[str] = []
    user = User(email="aluno@example.com", role="student", cohort_key="ano_1")

    monkeypatch.setattr(sidebar, "_apply_workspace_shell_styles", lambda: calls.append("styles"))
    monkeypatch.setattr(
        sidebar,
        "_render_authenticated_shell_sidebar",
        lambda **kwargs: calls.append("controls") or ("ano_1", "student"),
    )

    selected_project, current_workspace = sidebar.render_sidebar_ui(
        user=user,
        project_options=["ano_1"],
        selected_project="ano_1",
    )

    assert (selected_project, current_workspace) == ("ano_1", "student")
    assert calls == ["styles", "controls"]


def test_render_workspace_button_group_uses_full_width_segmented_control(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    fake_st = SimpleNamespace(
        segmented_control=lambda label, **kwargs: (
            calls.append({"label": label, **kwargs})
            or "professor"
        ),
    )

    monkeypatch.setattr(sidebar, "st", fake_st)

    selected_workspace = sidebar._render_workspace_button_group("student")

    assert selected_workspace == "professor"
    assert calls[0]["label"] == "Espa\u00e7o"
    assert calls[0]["options"] == ["student", "professor"]
    assert calls[0]["default"] == "student"
    assert calls[0]["key"] == "gm_workspace_segmented_control"
    assert calls[0]["label_visibility"] == "collapsed"
    assert calls[0]["width"] == "stretch"
    assert calls[0]["format_func"]("student") == "Aluno"
    assert calls[0]["format_func"]("professor") == "Professor"


def test_student_view_label_uses_portuguese_accents_without_mojibake() -> None:
    assert sidebar._format_student_view_label("practice") == "Questões"
    assert sidebar._format_student_view_label("stats") == "Estatísticas"


def test_normalize_filters_for_subject_group_shape_clears_full_subject_selection_in_single_subject_mode() -> None:
    normalized_filters = streamlit_app._normalize_filters_for_subject_group_shape(
        normalized_filters=QuestionFilterSelection(subjects=("databricks",), topics=()),
        subject_topic_groups=[SubjectTopicGroup(subject="databricks", topics=("structured streaming",))],
    )

    assert normalized_filters == QuestionFilterSelection(subjects=(), topics=())


def test_render_sidebar_logout_button_triggers_streamlit_logout(monkeypatch) -> None:
    calls: list[str] = []

    class FakeSidebar:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_st = SimpleNamespace(
        sidebar=FakeSidebar(),
        container=lambda: FakeSidebar(),
        html=lambda html: calls.append(html),
        button=lambda *args, **kwargs: True,
    )

    monkeypatch.setattr(sidebar, "st", fake_st)
    monkeypatch.setattr(sidebar, "trigger_logout", lambda: calls.append("logout"))

    sidebar.render_sidebar_logout_button()

    assert calls == [
        '<div class="gm-sidebar-section-hook gm-sidebar-logout-button-hook"></div>',
        '<div class="gm-sidebar-separator gm-sidebar-logout-separator-hook"></div>',
        "logout",
    ]


def test_apply_workspace_shell_styles_formats_logout_divider_spacing(monkeypatch) -> None:
    rendered_html: list[str] = []

    monkeypatch.setattr(
        sidebar.st,
        "markdown",
        lambda html, **kwargs: rendered_html.append(html),
    )

    sidebar._apply_workspace_shell_styles()

    assert len(rendered_html) == 1
    stylesheet = rendered_html[0]
    assert "gm-sidebar-logout-button-hook" in stylesheet
    assert "--gm-sidebar-section-margin-bottom: 16px;" in stylesheet
    assert "padding-top: var(--gm-sidebar-actions-padding-top) !important;" in stylesheet
    assert "gm-sidebar-logout-separator-hook" in stylesheet
    assert "margin-bottom: 0.78rem;" in stylesheet
    assert "background: #fff4f4 !important;" in stylesheet
    assert "border: 1px solid #f5a3a3 !important;" in stylesheet
    assert "color: #b91c1c !important;" in stylesheet
    assert '[data-testid="baseButton-secondary"]' in stylesheet
    assert "box-shadow: 0 0 0 0.16rem rgba(245, 163, 163, 0.32) !important;" in stylesheet
    assert "stSegmentedControl" in stylesheet
