import pandas as pd

from app import streamlit_app


class FakeQuestionRepository:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.received_cohort_key = "unset"

    def load_active_index_frame(self, *, cohort_key=None) -> pd.DataFrame:
        self.received_cohort_key = cohort_key
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
