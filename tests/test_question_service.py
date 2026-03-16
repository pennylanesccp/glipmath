import random

import pandas as pd
import pytest

from modules.domain.models import Question, QuestionAlternative
from modules.services.question_service import (
    build_display_alternatives,
    parse_question_bank_dataframe,
    select_next_question,
)
from modules.storage.schema_validation import WorksheetValidationError


def test_parse_question_bank_skips_inactive_and_malformed_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "id_question": 1,
                "statement": "Quanto e 2 + 2?",
                "correct_answer": {
                    "alternative_text": "4",
                    "explanation": "Somar 2 com 2 resulta em 4.",
                },
                "wrong_answers": [
                    {"alternative_text": "3", "explanation": "Faltou uma unidade."},
                    {"alternative_text": "5", "explanation": "Sobrou uma unidade."},
                ],
                "is_active": True,
            },
            {
                "id_question": 2,
                "statement": "Questao inativa",
                "correct_answer": {"alternative_text": "2", "explanation": None},
                "wrong_answers": [{"alternative_text": "3", "explanation": None}],
                "is_active": False,
            },
            {
                "id_question": 3,
                "statement": "Alternativas duplicadas",
                "correct_answer": {"alternative_text": "9", "explanation": None},
                "wrong_answers": [{"alternative_text": "9", "explanation": None}],
                "is_active": True,
            },
        ]
    )

    questions, issues = parse_question_bank_dataframe(frame)

    assert [question.id_question for question in questions] == [1]
    assert len(issues) == 1


def test_parse_question_bank_accepts_json_strings_for_nested_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "id_question": "1",
                "statement": "Quanto e 5 - 2?",
                "correct_answer": '{"alternative_text": "3", "explanation": "5 menos 2 e 3."}',
                "wrong_answers": '[{"alternative_text": "2", "explanation": "Subtraiu demais."}]',
                "is_active": "true",
            }
        ]
    )

    questions, issues = parse_question_bank_dataframe(frame)

    assert not issues
    assert questions[0].correct_answer.alternative_text == "3"
    assert questions[0].wrong_answers[0].alternative_text == "2"


def test_parse_question_bank_raises_for_duplicate_ids() -> None:
    frame = pd.DataFrame(
        [
            {
                "id_question": "1",
                "statement": "Pergunta 1",
                "correct_answer": {"alternative_text": "1", "explanation": None},
                "wrong_answers": [{"alternative_text": "2", "explanation": None}],
            },
            {
                "id_question": "1",
                "statement": "Pergunta 2",
                "correct_answer": {"alternative_text": "3", "explanation": None},
                "wrong_answers": [{"alternative_text": "4", "explanation": None}],
            },
        ]
    )

    with pytest.raises(WorksheetValidationError):
        parse_question_bank_dataframe(frame)


def test_build_display_alternatives_randomizes_and_keeps_single_correct_answer() -> None:
    question = Question(
        id_question=1,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4", "Explicacao correta."),
        wrong_answers=(
            QuestionAlternative("3", "Explicacao errada 1."),
            QuestionAlternative("5", "Explicacao errada 2."),
        ),
    )

    alternatives = build_display_alternatives(question, randomizer=random.Random(3))

    assert sorted(item.alternative_text for item in alternatives) == ["3", "4", "5"]
    assert sum(1 for item in alternatives if item.is_correct) == 1
    assert [item.option_id for item in alternatives] != ["correct", "wrong_1", "wrong_2"]


def test_select_next_question_prioritizes_unseen_questions() -> None:
    questions = [
        Question(
            id_question=1,
            statement="Q1",
            correct_answer=QuestionAlternative("1"),
            wrong_answers=(QuestionAlternative("2"),),
        ),
        Question(
            id_question=2,
            statement="Q2",
            correct_answer=QuestionAlternative("2"),
            wrong_answers=(QuestionAlternative("3"),),
        ),
    ]

    selected = select_next_question(
        questions,
        answered_question_ids={1},
        randomizer=random.Random(7),
    )

    assert selected is not None
    assert selected.id_question == 2
