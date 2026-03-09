import random

import pandas as pd
import pytest

from modules.domain.models import Question
from modules.services.question_service import parse_question_bank_dataframe, select_next_question
from modules.storage.schema_validation import WorksheetValidationError


def test_parse_question_bank_skips_inactive_and_malformed_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "id_question": "1",
                "source": "Livro",
                "statement": "2 + 2 = ?",
                "choice_a": "3",
                "choice_b": "4",
                "choice_c": "5",
                "choice_d": "6",
                "choice_e": "",
                "correct_choice": "B",
                "is_active": "true",
            },
            {
                "id_question": "2",
                "source": "Livro",
                "statement": "Questao inativa",
                "choice_a": "1",
                "choice_b": "2",
                "choice_c": "3",
                "choice_d": "4",
                "choice_e": "",
                "correct_choice": "A",
                "is_active": "false",
            },
            {
                "id_question": "3",
                "source": "Livro",
                "statement": "Faltando alternativa",
                "choice_a": "1",
                "choice_b": "2",
                "choice_c": "3",
                "choice_d": "",
                "choice_e": "",
                "correct_choice": "A",
                "is_active": "true",
            },
        ]
    )

    questions, issues = parse_question_bank_dataframe(frame)

    assert [question.id_question for question in questions] == [1]
    assert len(issues) == 1


def test_parse_question_bank_raises_for_duplicate_ids() -> None:
    frame = pd.DataFrame(
        [
            {
                "id_question": "1",
                "source": "Livro",
                "statement": "Pergunta 1",
                "choice_a": "1",
                "choice_b": "2",
                "choice_c": "3",
                "choice_d": "4",
                "correct_choice": "A",
            },
            {
                "id_question": "1",
                "source": "Livro",
                "statement": "Pergunta 2",
                "choice_a": "1",
                "choice_b": "2",
                "choice_c": "3",
                "choice_d": "4",
                "correct_choice": "B",
            },
        ]
    )

    with pytest.raises(WorksheetValidationError):
        parse_question_bank_dataframe(frame)


def test_select_next_question_prioritizes_unseen_questions() -> None:
    questions = [
        Question(
            id_question=1,
            source="A",
            statement="Q1",
            choices={"A": "1", "B": "2", "C": "3", "D": "4"},
            correct_choice="A",
        ),
        Question(
            id_question=2,
            source="B",
            statement="Q2",
            choices={"A": "1", "B": "2", "C": "3", "D": "4"},
            correct_choice="B",
        ),
    ]

    selected = select_next_question(
        questions,
        answered_question_ids={1},
        randomizer=random.Random(7),
    )

    assert selected is not None
    assert selected.id_question == 2
