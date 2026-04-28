import random

import pandas as pd
import pytest

from modules.domain.models import Question, QuestionAlternative, QuestionIndexEntry, User
from modules.services.question_service import (
    build_display_alternatives,
    build_project_options,
    build_subject_options,
    build_subject_topic_groups,
    QuestionFilterSelection,
    filter_question_index_by_project,
    filter_question_ids_by_filters,
    filter_question_ids_by_subject,
    format_question_filter_label,
    format_project_label,
    format_subject_label,
    format_subject_topic_filter_label,
    format_topic_label,
    find_valid_question_bank_row_indexes,
    normalize_multi_question_filters,
    normalize_question_filters,
    parse_question_bank_dataframe,
    parse_question_id_dataframe,
    parse_question_index_dataframe,
    parse_project_options_dataframe,
    parse_single_question_dataframe,
    select_question_batch_ids,
    select_next_question,
    select_next_question_id,
)
from modules.services.user_service import (
    resolve_available_project_options,
    resolve_effective_project_for_user,
    resolve_question_scope_for_user,
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
                "subject": "matematica",
                "cohort_key": "Ano_1",
                "is_active": "true",
            }
        ]
    )

    questions, issues = parse_question_bank_dataframe(frame)

    assert not issues
    assert questions[0].correct_answer.alternative_text == "3"
    assert questions[0].wrong_answers[0].alternative_text == "2"
    assert questions[0].subject == "matematica"
    assert questions[0].cohort_key == "ano_1"


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


def test_select_next_question_id_prioritizes_unseen_question_ids() -> None:
    selected = select_next_question_id(
        [1, 2, 3],
        answered_question_ids={1, 3},
        randomizer=random.Random(7),
    )

    assert selected == 2


def test_select_question_batch_ids_excludes_answered_and_limits_prefetch_size() -> None:
    selected = select_question_batch_ids(
        [1, 2, 3, 4, 5],
        excluded_question_ids={2, 5},
        limit=2,
        randomizer=random.Random(3),
    )

    assert len(selected) == 2
    assert set(selected).issubset({1, 3, 4})
    assert 2 not in selected
    assert 5 not in selected


def test_parse_question_id_dataframe_reads_integer_ids() -> None:
    frame = pd.DataFrame([{"id_question": "10"}, {"id_question": 22}])

    question_ids, issues = parse_question_id_dataframe(frame)

    assert question_ids == [10, 22]
    assert issues == []


def test_parse_question_index_dataframe_reads_subject_metadata() -> None:
    frame = pd.DataFrame(
        [
            {"id_question": "10", "subject": "Matematica", "topic": "divisao", "cohort_key": "Ano_1"},
            {"id_question": 22, "subject": None, "topic": None, "cohort_key": None},
        ]
    )

    entries, issues = parse_question_index_dataframe(frame)

    assert issues == []
    assert entries == [
        QuestionIndexEntry(id_question=10, subject="matematica", topic="divisao", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=22, subject=None, topic=None, cohort_key=None),
    ]


def test_subject_option_helpers_build_and_filter_active_ids() -> None:
    question_index = [
        QuestionIndexEntry(id_question=1, subject="Matematica", topic="divisao", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=2, subject="Portugues", topic="gramatica", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=3, subject="Matematica", topic="radiciacao", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=4, subject=None, topic=None, cohort_key="ano_1"),
    ]

    assert build_subject_options(question_index) == ["Tudo", "matematica", "portugues"]
    assert filter_question_ids_by_subject(question_index, None) == [1, 2, 3, 4]
    assert filter_question_ids_by_subject(question_index, "Matematica") == [1, 3]
    assert filter_question_ids_by_subject(question_index, "Matemática", topic="Radiciação") == [3]

    subject_topic_groups = build_subject_topic_groups(question_index)
    assert [(group.subject, group.topics) for group in subject_topic_groups] == [
        ("matematica", ("divisao", "radiciacao")),
        ("portugues", ("gramatica",)),
    ]


def test_multi_question_filters_normalize_and_intersect_subjects_with_topics() -> None:
    question_index = [
        QuestionIndexEntry(id_question=1, subject="Matematica", topic="divisao", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=2, subject="Matematica", topic="radiciacao", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=3, subject="Portugues", topic="gramatica", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=4, subject="Ciencias", topic="ecologia", cohort_key="ano_1"),
    ]

    filters = normalize_multi_question_filters(
        question_index,
        subjects=["Matematica", "MateriaInvalida"],
        topics=[("Matematica", "radiciacao"), ("Matematica", "topico_invalido"), ("Portugues", "gramatica")],
    )

    assert filters == QuestionFilterSelection(
        subjects=("matematica",),
        topics=(("matematica", "radiciacao"),),
    )
    assert filter_question_ids_by_filters(question_index, filters) == [2]

    topic_only_filters = normalize_multi_question_filters(
        question_index,
        subjects=[],
        topics=[("Portugues", "gramatica")],
    )

    assert topic_only_filters == QuestionFilterSelection(
        topics=(("portugues", "gramatica"),),
    )
    assert filter_question_ids_by_filters(question_index, topic_only_filters) == [3]


def test_format_question_filter_label_summarizes_multi_selection_state() -> None:
    assert format_question_filter_label(QuestionFilterSelection()) == "Tudo"
    assert (
        format_question_filter_label(QuestionFilterSelection(subjects=("matematica",)))
        == "Matemática"
    )
    assert (
        format_question_filter_label(QuestionFilterSelection(topics=(("matematica", "divisao"),)))
        == "Matemática / Divisão"
    )
    assert (
        format_question_filter_label(
            QuestionFilterSelection(
                subjects=("matematica",),
                topics=(("matematica", "divisao"),),
            )
        )
        == "Matemática / Divisão"
    )


def test_project_option_helpers_build_filter_and_format_labels() -> None:
    question_index = [
        QuestionIndexEntry(id_question=1, subject="Matematica", topic="divisao", cohort_key="crescer_e_conectar"),
        QuestionIndexEntry(id_question=2, subject="Portugues", topic="gramatica", cohort_key="ano_1"),
        QuestionIndexEntry(id_question=3, subject="Matematica", topic="radiciacao", cohort_key="crescer_e_conectar"),
        QuestionIndexEntry(id_question=4, subject=None, topic=None, cohort_key=None),
    ]

    assert build_project_options(question_index) == ["ano_1", "crescer_e_conectar"]
    assert [entry.id_question for entry in filter_question_index_by_project(question_index, "crescer_e_conectar")] == [1, 3]
    assert format_project_label("crescer_e_conectar") == "Crescer e Conectar"
    assert format_project_label("ano_1") == "Ano 1"
    assert format_subject_label("matematica") == "Matemática"
    assert format_topic_label("auto_loader") == "Auto Loader"
    assert format_topic_label("radiciacao") == "Radiciação"
    assert format_subject_topic_filter_label("matematica", "divisao") == "Matemática · Divisão"


def test_format_project_label_uses_explicit_accented_project_names() -> None:
    assert format_project_label("certificacao_databricks") == "Certificação Databricks"
    assert format_project_label("rumo_etec") == "Rumo à ETEC"


def test_format_topic_label_uses_english_databricks_topic_names() -> None:
    assert (
        format_topic_label("fundamentos_notebooks_jobs_lakeflow")
        == "Developing Code for Data Processing using Python and SQL"
    )
    assert format_topic_label("autoloader_e_pipelines_declarativas") == "Data Ingestion & Acquisition"
    assert format_topic_label("structured_streaming") == "Data Transformation, Cleansing and Quality"
    assert format_topic_label("delta_sharing_e_federation") == "Data Sharing and Federation"
    assert format_topic_label("jobs_alertas_e_spark_ui") == "Monitoring and Alerting"
    assert format_topic_label("delta_otimizacao_e_storage") == "Cost & Performance Optimisation"
    assert format_topic_label("seguranca_views_e_secrets") == "Ensuring Data Security and Compliance"
    assert format_topic_label("governanca_catalogo_e_metadados") == "Data Governance"
    assert format_topic_label("troubleshooting_e_performance") == "Debugging and Deploying"
    assert format_topic_label("medallion_modelagem_e_dimensoes") == "Data Modelling"


def test_subject_filter_still_works_after_cohort_scoping() -> None:
    scoped_question_index = [
        QuestionIndexEntry(id_question=11, subject="Matematica", topic="divisao", cohort_key="ano_2"),
        QuestionIndexEntry(id_question=12, subject="Portugues", topic="gramatica", cohort_key="ano_2"),
        QuestionIndexEntry(id_question=13, subject="Matematica", topic="radiciacao", cohort_key="ano_2"),
    ]

    assert filter_question_ids_by_subject(scoped_question_index, "Matematica") == [11, 13]
    assert normalize_question_filters(
        scoped_question_index,
        subject="Matematica",
        topic="topico_invalido",
    ) == ("matematica", None)


def test_parse_project_options_dataframe_normalizes_and_deduplicates_values() -> None:
    project_options, issues = parse_project_options_dataframe(
        pd.DataFrame(
            [
                {"cohort_key": "Ano_1"},
                {"cohort_key": "crescer_e_conectar"},
                {"cohort_key": "ano_1"},
                {"cohort_key": None},
            ]
        )
    )

    assert issues == []
    assert project_options == ["ano_1", "crescer_e_conectar"]


def test_resolve_question_scope_for_student_returns_specific_cohort() -> None:
    user = User(email="ana@example.com", role="student", cohort_key="ano_3")

    assert resolve_question_scope_for_user(user) == "ano_3"


def test_resolve_question_scope_for_teacher_returns_global_scope() -> None:
    user = User(email="prof@example.com", role="teacher", cohort_key="all")

    assert resolve_question_scope_for_user(user) is None


def test_resolve_effective_project_for_teacher_returns_selected_project() -> None:
    user = User(email="prof@example.com", role="teacher", cohort_key="all")

    assert resolve_effective_project_for_user(user, selected_project="crescer_e_conectar") == "crescer_e_conectar"


def test_resolve_effective_project_for_multi_project_student_prefers_selected_project() -> None:
    user = User(
        email="ana@example.com",
        role="student",
        cohort_key="crescer_e_conectar",
        accessible_cohort_keys=("crescer_e_conectar", "rumo_etec"),
    )

    assert resolve_effective_project_for_user(user, selected_project="rumo_etec") == "rumo_etec"
    assert resolve_effective_project_for_user(user, selected_project="projeto_invalido") == "crescer_e_conectar"


def test_resolve_available_project_options_uses_explicit_access_list_for_non_global_users() -> None:
    user = User(
        email="prof@example.com",
        role="teacher",
        cohort_key="crescer_e_conectar",
        accessible_cohort_keys=("crescer_e_conectar", "rumo_etec"),
    )

    assert resolve_available_project_options(
        user,
        active_project_options=["certificacao_databricks", "rumo_etec", "crescer_e_conectar"],
    ) == ["crescer_e_conectar", "rumo_etec"]


def test_resolve_available_project_options_keeps_explicit_projects_even_without_active_questions() -> None:
    user = User(
        email="prof@example.com",
        role="teacher",
        cohort_key="crescer_e_conectar",
        accessible_cohort_keys=("crescer_e_conectar", "rumo_etec"),
    )

    assert resolve_available_project_options(
        user,
        active_project_options=["crescer_e_conectar"],
    ) == ["crescer_e_conectar", "rumo_etec"]


def test_resolve_available_project_options_uses_active_projects_for_global_access() -> None:
    user = User(email="admin@example.com", role="admin", cohort_key="all")

    assert resolve_available_project_options(
        user,
        active_project_options=["certificacao_databricks", "rumo_etec", "crescer_e_conectar"],
    ) == ["certificacao_databricks", "crescer_e_conectar", "rumo_etec"]


def test_parse_single_question_dataframe_returns_single_question() -> None:
    frame = pd.DataFrame(
        [
            {
                "id_question": 1,
                "statement": "Quanto e 2 + 2?",
                "correct_answer": {"alternative_text": "4", "explanation": None},
                "wrong_answers": [{"alternative_text": "3", "explanation": None}],
                "cohort_key": "ano_1",
                "is_active": True,
            }
        ]
    )

    question, issues = parse_single_question_dataframe(frame)

    assert not issues
    assert question is not None
    assert question.id_question == 1
    assert question.cohort_key == "ano_1"


def test_find_valid_question_bank_row_indexes_skips_duplicate_and_malformed_rows() -> None:
    rows = [
        {
            "id_question": 1,
            "statement": "Pergunta valida",
            "correct_answer": {"alternative_text": "1", "explanation": None},
            "wrong_answers": [{"alternative_text": "2", "explanation": None}],
            "is_active": True,
        },
        {
            "id_question": 2,
            "statement": "Duplicada A",
            "correct_answer": {"alternative_text": "3", "explanation": None},
            "wrong_answers": [{"alternative_text": "4", "explanation": None}],
            "is_active": True,
        },
        {
            "id_question": 2,
            "statement": "Duplicada B",
            "correct_answer": {"alternative_text": "5", "explanation": None},
            "wrong_answers": [{"alternative_text": "6", "explanation": None}],
            "is_active": True,
        },
        {
            "id_question": 3,
            "statement": "",
            "correct_answer": {"alternative_text": "7", "explanation": None},
            "wrong_answers": [{"alternative_text": "8", "explanation": None}],
            "is_active": True,
        },
    ]

    valid_indexes, issues = find_valid_question_bank_row_indexes(rows)

    assert valid_indexes == [0]
    assert [issue.row_number for issue in issues] == [3, 4, 5]
    assert issues[0].message == "id_question must be unique; duplicate value 2."
    assert issues[2].message == "statement cannot be blank."
