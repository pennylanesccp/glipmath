import pandas as pd
from types import SimpleNamespace

from app import streamlit_app
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
        rerun=lambda: (_ for _ in ()).throw(AssertionError("should not rerun")),
    )

    monkeypatch.setattr(streamlit_app, "st", fake_st)
    monkeypatch.setattr(streamlit_app, "get_project_filter", lambda: "crescer_e_conectar")

    selected_project, current_workspace = streamlit_app._render_authenticated_shell_sidebar(
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
        caption=lambda *args, **kwargs: None,
        selectbox=lambda *args, **kwargs: "rumo_etec",
        segmented_control=lambda *args, **kwargs: "student",
        rerun=lambda: (_ for _ in ()).throw(AssertionError("should not rerun")),
    )

    monkeypatch.setattr(streamlit_app, "st", fake_st)
    monkeypatch.setattr(streamlit_app, "get_project_filter", lambda: "rumo_etec")
    monkeypatch.setattr(streamlit_app, "get_current_workspace", lambda: "student")

    selected_project, current_workspace = streamlit_app._render_authenticated_shell_sidebar(
        user=user,
        project_options=["crescer_e_conectar", "rumo_etec"],
        selected_project="rumo_etec",
    )

    assert selected_project == "rumo_etec"
    assert current_workspace == "student"


def test_normalize_filters_for_subject_group_shape_clears_full_subject_selection_in_single_subject_mode() -> None:
    normalized_filters = streamlit_app._normalize_filters_for_subject_group_shape(
        normalized_filters=QuestionFilterSelection(subjects=("databricks",), topics=()),
        subject_topic_groups=[SubjectTopicGroup(subject="databricks", topics=("structured streaming",))],
    )

    assert normalized_filters == QuestionFilterSelection(subjects=(), topics=())
