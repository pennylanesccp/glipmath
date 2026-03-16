from __future__ import annotations

import json

import pandas as pd
from google.cloud import bigquery

from modules.domain.models import QuestionAlternative
from modules.storage.bigquery_client import BigQueryClient


class QuestionRepository:
    """Access to the nested question bank table."""

    def __init__(self, bigquery_client: BigQueryClient, table_id: str) -> None:
        self._bigquery_client = bigquery_client
        self._table_id = table_id

    def load_frame(self, *, only_active: bool = True) -> pd.DataFrame:
        """Load questions from BigQuery."""

        where_clause = "WHERE is_active = TRUE" if only_active else ""

        query = f"""
            SELECT
                id_question,
                statement,
                correct_answer,
                wrong_answers,
                subject,
                topic,
                difficulty,
                source,
                is_active,
                created_at_utc,
                updated_at_utc
            FROM `{self._table_id}`
            {where_clause}
            ORDER BY id_question
        """
        return self._bigquery_client.query_to_dataframe(query)

    def load_active_id_frame(self) -> pd.DataFrame:
        """Load the active question identifiers only."""

        query = f"""
            SELECT
                id_question
            FROM `{self._table_id}`
            WHERE is_active = TRUE
        """
        return self._bigquery_client.query_to_dataframe(query)

    def load_question_frame_by_id(self, id_question: int) -> pd.DataFrame:
        """Load a single active question by identifier."""

        query = f"""
            SELECT
                id_question,
                statement,
                correct_answer,
                wrong_answers,
                subject,
                topic,
                difficulty,
                source,
                is_active
            FROM `{self._table_id}`
            WHERE is_active = TRUE
              AND id_question = @id_question
            LIMIT 1
        """
        return self._bigquery_client.query_to_dataframe(
            query,
            parameters=[bigquery.ScalarQueryParameter("id_question", "INT64", id_question)],
        )

    def load_missing_explanations_frame(self, *, limit: int | None = None) -> pd.DataFrame:
        """Load active questions that still need one or more explanations."""

        limit_clause = "LIMIT @limit" if limit is not None else ""
        parameters = (
            [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
            if limit is not None
            else None
        )
        query = f"""
            SELECT
                id_question,
                statement,
                correct_answer,
                wrong_answers,
                subject,
                topic,
                difficulty,
                source,
                is_active,
                created_at_utc,
                updated_at_utc
            FROM `{self._table_id}`
            WHERE is_active = TRUE
              AND (
                correct_answer.explanation IS NULL
                OR TRIM(correct_answer.explanation) = ''
                OR EXISTS (
                    SELECT 1
                    FROM UNNEST(wrong_answers) AS wrong_answer
                    WHERE wrong_answer.explanation IS NULL
                       OR TRIM(wrong_answer.explanation) = ''
                )
              )
            ORDER BY id_question
            {limit_clause}
        """
        return self._bigquery_client.query_to_dataframe(query, parameters=parameters)

    def update_question_explanations(
        self,
        *,
        id_question: int,
        correct_answer: QuestionAlternative,
        wrong_answers: tuple[QuestionAlternative, ...],
    ) -> None:
        """Update the explanation fields for one question row."""

        wrong_answers_json = json.dumps(
            [
                {
                    "alternative_text": answer.alternative_text,
                    "explanation": answer.explanation,
                }
                for answer in wrong_answers
            ],
            ensure_ascii=False,
        )
        query = f"""
            UPDATE `{self._table_id}`
            SET
                correct_answer = STRUCT(
                    @correct_alternative_text AS alternative_text,
                    @correct_explanation AS explanation
                ),
                wrong_answers = ARRAY(
                    SELECT AS STRUCT
                        JSON_VALUE(wrong_answer, '$.alternative_text') AS alternative_text,
                        JSON_VALUE(wrong_answer, '$.explanation') AS explanation
                    FROM UNNEST(JSON_QUERY_ARRAY(@wrong_answers_json, '$')) AS wrong_answer
                ),
                updated_at_utc = CURRENT_TIMESTAMP()
            WHERE id_question = @id_question
        """
        parameters = [
            bigquery.ScalarQueryParameter("id_question", "INT64", id_question),
            bigquery.ScalarQueryParameter(
                "correct_alternative_text",
                "STRING",
                correct_answer.alternative_text,
            ),
            bigquery.ScalarQueryParameter(
                "correct_explanation",
                "STRING",
                correct_answer.explanation,
            ),
            bigquery.ScalarQueryParameter(
                "wrong_answers_json",
                "STRING",
                wrong_answers_json,
            ),
        ]
        self._bigquery_client.execute(query, parameters=parameters)
