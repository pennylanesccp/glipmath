import pandas as pd

from app import streamlit_app
from modules.domain.models import User


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
