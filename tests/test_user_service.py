import pytest

from modules.domain.models import UserAccessEntry
from modules.services.user_service import (
    build_student_access_removal_target,
    build_student_access_row,
    has_active_project_access,
)


def test_build_student_access_row_normalizes_email_and_project() -> None:
    row = build_student_access_row(
        " ALUNO@Example.com ",
        cohort_key="Certificacao_Databricks",
    )

    assert row["user_email"] == "aluno@example.com"
    assert row["role"] == "student"
    assert row["cohort_key"] == "certificacao_databricks"
    assert row["is_active"] is True
    assert row["created_at_utc"] == row["updated_at_utc"]


def test_has_active_project_access_accepts_direct_or_global_access() -> None:
    direct_access = UserAccessEntry(
        user_email="aluno@example.com",
        role="student",
        cohort_key="rumo_etec",
        is_active=True,
    )
    global_access = UserAccessEntry(
        user_email="aluno@example.com",
        role="admin",
        cohort_key="all",
        is_active=True,
    )

    assert has_active_project_access([direct_access], cohort_key="rumo_etec") is True
    assert has_active_project_access([global_access], cohort_key="rumo_etec") is True
    assert has_active_project_access([direct_access], cohort_key="crescer_e_conectar") is False


def test_build_student_access_removal_target_normalizes_email_and_project() -> None:
    target = build_student_access_removal_target(
        " ALUNO@Example.com ",
        cohort_key="Certificacao_Databricks",
    )

    assert target == {
        "user_email": "aluno@example.com",
        "cohort_key": "certificacao_databricks",
    }


def test_build_student_access_removal_target_rejects_global_project() -> None:
    with pytest.raises(ValueError, match="projeto específico"):
        build_student_access_removal_target("aluno@example.com", cohort_key="all")
